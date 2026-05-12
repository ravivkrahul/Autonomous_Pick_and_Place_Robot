#!/usr/bin/env python3
"""

- Encoders are used ONLY for distance target
- Straight motion maintains a fixed IMU heading using PID
- Heading reference is taken at the start of each straight segment
- Left turns use current IMU heading as reference and turn 90 deg left

Logs:
    time, imu_x, x, y, phase

CSV:
    encoder_imu_rectangle.csv
"""

import RPi.GPIO as GPIO
import time
import csv
import serial
import re
import math
import threading
import sys
import select
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "data" / "encoder_imu_fusion" / "encoder_imu_rectangle.csv"
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# PINS
# ============================================================
IN1, IN2, IN3, IN4 = 6, 13, 19, 26
ENC_LEFT, ENC_RIGHT = 4, 18

# ============================================================
# ROBOT CONSTANTS
# ============================================================
WHEEL_DIAMETER = 0.065
WHEEL_CIRCUM = math.pi * WHEEL_DIAMETER
COUNTS_PER_REV = 10
M_PER_COUNT = WHEEL_CIRCUM / COUNTS_PER_REV

# Rectangle dimensions (meters)
RECT_LONG = 1.4
RECT_SHORT = 1.0

# ============================================================
# CONTROL TIMESTEP
# ============================================================
DT = 0.02

# ============================================================
# STRAIGHT MOTION: HEADING PID
# Encoder counts only decide when to stop
# ============================================================
BASE_PWM_LEFT = 58
BASE_PWM_RIGHT = 62
PWM_MIN_FWD = 35
PWM_MAX_FWD = 100

KP_HEAD = 1.0
KI_HEAD = 0.02
KD_HEAD = 0.10
I_CLAMP_HEAD = 15.0

# ============================================================
# LEFT TURN CONTROL
# Keep torque high enough
# ============================================================
TURN_PWM_MIN = 60
TURN_PWM_MAX = 76
TURN_TOL = 1.1

KP_TURN = 0.55
KI_TURN = 0.03
I_CLAMP_TURN = 20.0

# ============================================================
# GLOBALS
# ============================================================
left_count = 0
right_count = 0
prev_left = 0
prev_right = 0
enc_running = True

x_pos = 0.0
y_pos = 0.0
heading_deg = 0.0
last_imu_x = 0.0

# ============================================================
# GPIO SETUP
# ============================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(ENC_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ENC_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

pwm1 = GPIO.PWM(IN1, 1000)
pwm2 = GPIO.PWM(IN2, 1000)
pwm3 = GPIO.PWM(IN3, 1000)
pwm4 = GPIO.PWM(IN4, 1000)

for p in [pwm1, pwm2, pwm3, pwm4]:
    p.start(0)

# ============================================================
# IMU SERIAL
# ============================================================
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.1)
time.sleep(2)

ser.reset_input_buffer()
ser.reset_output_buffer()

last_imu_x = 0.0
last_raw_line = ""

def imu_x():
    global last_imu_x, last_raw_line

    latest_val = None

    # drain all available serial lines and keep only the newest one
    while ser.in_waiting > 0:
        line = ser.readline().decode(errors='ignore').strip()

        if not line:
            continue

        last_raw_line = line
        nums = re.findall(r'-?\d+\.?\d*', line)

        if len(nums) >= 1:
            val = float(nums[0])

            # ignore invalid zeros if your IMU sends them during startup
            if val != 0:
                latest_val = val

    if latest_val is not None:
        last_imu_x = latest_val

    return last_imu_x

def wait_for_confirmation():
    print("Waiting for fresh IMU data. Press ENTER when heading looks correct.\n")

    # warm up a little and clear stale startup bytes
    t0 = time.time()
    while time.time() - t0 < 1.0:
        imu_x()
        time.sleep(0.02)

    last_seen = None
    changed_count = 0

    while True:
        heading = imu_x()

        if last_seen is None or abs(heading - last_seen) > 0.01:
            changed_count += 1
            last_seen = heading

        print(
            f"\rLive IMU_X: {heading:8.3f} deg   updates:{changed_count:3d}   Press ENTER to start rectangle...",
            end="",
            flush=True
        )

        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            line = sys.stdin.readline()
            if line == "\n" or line == "":
                print(f"\nConfirmed heading: {heading:.3f} deg")
                return heading

# ============================================================
# ENCODER THREAD
# ============================================================
def encoder_loop():
    global left_count, right_count, prev_left, prev_right

    while enc_running:
        curr_left = GPIO.input(ENC_LEFT)
        curr_right = GPIO.input(ENC_RIGHT)

        if prev_left == 0 and curr_left == 1:
            left_count += 1
        if prev_right == 0 and curr_right == 1:
            right_count += 1

        prev_left = curr_left
        prev_right = curr_right
        time.sleep(0.001)

def reset_counts():
    global left_count, right_count
    left_count = 0
    right_count = 0

# ============================================================
# MOTOR HELPERS
# ============================================================
def set_motors(l_fwd, l_bwd, r_fwd, r_bwd):
    pwm1.ChangeDutyCycle(max(0, min(100, l_fwd)))
    pwm2.ChangeDutyCycle(max(0, min(100, l_bwd)))
    pwm4.ChangeDutyCycle(max(0, min(100, r_fwd)))
    pwm3.ChangeDutyCycle(max(0, min(100, r_bwd)))

def stop():
    set_motors(0, 0, 0, 0)

def drive_forward(left_duty, right_duty):
    left_duty = max(PWM_MIN_FWD, min(PWM_MAX_FWD, left_duty))
    right_duty = max(PWM_MIN_FWD, min(PWM_MAX_FWD, right_duty))
    set_motors(left_duty, 0, right_duty, 0)

def drive_pivot_left(pwm):
    pwm = max(TURN_PWM_MIN, min(TURN_PWM_MAX, pwm))
    set_motors(0, pwm, pwm, 0)

def drive_pivot_right(pwm):
    pwm = max(TURN_PWM_MIN, min(TURN_PWM_MAX, pwm))
    set_motors(pwm, 0, 0, pwm)

# ============================================================
# CSV LOGGING
# ============================================================
f = open(CSV_PATH, "w", newline="")
writer = csv.writer(f)
writer.writerow(["time", "imu_x", "x", "y", "phase"])

t0 = time.time()

def log_row(phase):
    writer.writerow([
        round(time.time() - t0, 3),
        round(imu_x(), 3),
        round(x_pos, 4),
        round(y_pos, 4),
        phase
    ])

# ============================================================
# POSE UPDATE
# Use latest actual heading after each segment
# ============================================================
def update_pose_forward(distance_m):
    global x_pos, y_pos, heading_deg
    heading_deg = imu_x()
    th = math.radians(heading_deg)
    x_pos += distance_m * math.cos(th)
    y_pos += distance_m * math.sin(th)

# ============================================================
# ANGLE HELPERS
# ============================================================
def wrap_to_180(angle):
    return (angle + 180.0) % 360.0 - 180.0

# ============================================================
# STRAIGHT MOTION
# Encoders decide distance only
# IMU heading PID keeps robot on fixed heading
#
# SIGN FIX:
# left turn / left drift makes imu_x decrease
# so if current heading falls below reference,
# heading_error = reference - current becomes positive
# positive correction should steer robot RIGHT:
#   left PWM up, right PWM down
# ============================================================
def forward_distance_hold_heading(distance_m, phase_name):
    global left_count, right_count

    reset_counts()
    target_counts = int(distance_m / M_PER_COUNT)

    heading_ref = imu_x()
    integral = 0.0
    prev_error = 0.0
    last_log = time.time()

    print(f"\n{phase_name}: heading_ref={heading_ref:.2f}, target_counts={target_counts}")

    while left_count < target_counts and right_count < target_counts:
        current_heading = imu_x()

        # Correct sign:
        # if robot drifts left, current heading decreases,
        # so error becomes positive and we steer RIGHT
        heading_error = wrap_to_180(heading_ref - current_heading)

        integral += heading_error * DT
        integral = max(-I_CLAMP_HEAD, min(I_CLAMP_HEAD, integral))

        derivative = (heading_error - prev_error) / DT
        prev_error = heading_error

        correction = (
            KP_HEAD * heading_error +
            KI_HEAD * integral +
            KD_HEAD * derivative
        )

        # positive correction -> steer right
        # increase left wheel, decrease right wheel
        lp = BASE_PWM_LEFT + correction
        rp = BASE_PWM_RIGHT - correction

        lp = max(PWM_MIN_FWD, min(PWM_MAX_FWD, lp))
        rp = max(PWM_MIN_FWD, min(PWM_MAX_FWD, rp))

        drive_forward(lp, rp)

        if time.time() - last_log >= 0.05:
            log_row(phase_name)
            last_log = time.time()

        time.sleep(DT)

    stop()
    time.sleep(0.2)

    actual_distance = ((left_count + right_count) / 2.0) * M_PER_COUNT
    update_pose_forward(actual_distance)
    log_row(f"{phase_name}_done")

# ============================================================
# LEFT TURN BY 90 DEG USING CURRENT IMU AS REFERENCE
# left turn makes imu_x decrease
# ============================================================
def pivot_left_by_90(phase_name):
    global heading_deg

    reference_heading = imu_x()
    target_turn = 90.0

    print(f"\n{phase_name}: ref={reference_heading:.2f}")

    integral = 0.0
    last_log = time.time()

    while True:
        current = imu_x()

        # signed left-turn progress from reference
        delta = wrap_to_180(reference_heading - current)
        turned_left = max(0.0, delta)

        error = target_turn - turned_left

        if turned_left > 5.0 and error <= TURN_TOL:
            break

        integral += error * DT
        integral = max(-I_CLAMP_TURN, min(I_CLAMP_TURN, integral))

        pwm = KP_TURN * error + KI_TURN * integral
        pwm = max(TURN_PWM_MIN, min(TURN_PWM_MAX, pwm))

        drive_pivot_left(pwm)

        if time.time() - last_log >= 0.05:
            log_row(phase_name)
            last_log = time.time()

        time.sleep(0.02)

    stop()
    time.sleep(0.08)

    heading_deg = imu_x()
    log_row(f"{phase_name}_done")

    final_delta = wrap_to_180(reference_heading - heading_deg)
    final_turn = max(0.0, final_delta)
    print(f"{phase_name}: final={heading_deg:.2f}, turned_left={final_turn:.2f}")

# ============================================================
# OPTIONAL AUTO TURN HELPER
# not used in main rectangle
# ============================================================
def turn_to_heading_auto(target_heading, phase_name):
    global heading_deg
    integral = 0.0
    last_log = time.time()

    while True:
        current = imu_x()
        error_signed = wrap_to_180(target_heading - current)

        if abs(error_signed) <= TURN_TOL:
            break

        integral += error_signed * DT
        integral = max(-I_CLAMP_TURN, min(I_CLAMP_TURN, integral))

        pwm = abs(KP_TURN * error_signed + KI_TURN * integral)
        pwm = max(TURN_PWM_MIN, min(TURN_PWM_MAX, pwm))

        if error_signed > 0:
            drive_pivot_left(pwm)
        else:
            drive_pivot_right(pwm)

        if time.time() - last_log >= 0.05:
            log_row(phase_name)
            last_log = time.time()

        time.sleep(0.02)

    stop()
    time.sleep(0.08)

    heading_deg = imu_x()
    log_row(f"{phase_name}_done")

# ============================================================
# MAIN
# ============================================================
enc_thread = threading.Thread(target=encoder_loop, daemon=True)
enc_thread.start()
time.sleep(0.1)

try:
    start_heading = wait_for_confirmation()
    heading_deg = start_heading
    log_row("start")

    forward_distance_hold_heading(RECT_LONG, "forward_1")
    pivot_left_by_90("turn_1")

    forward_distance_hold_heading(RECT_SHORT, "forward_2")
    pivot_left_by_90("turn_2")

    forward_distance_hold_heading(RECT_LONG, "forward_3")
    pivot_left_by_90("turn_3")

    forward_distance_hold_heading(RECT_SHORT, "forward_4")
    pivot_left_by_90("turn_4")

    log_row("done")
    print("\nRectangle complete.")

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    enc_running = False
    stop()
    time.sleep(0.2)

    for p in [pwm1, pwm2, pwm3, pwm4]:
        p.stop()

    GPIO.cleanup()
    f.close()
    ser.close()
