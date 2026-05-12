#!/usr/bin/env python3
"""
ENCODER-ONLY RECTANGLE
Logs: time, imu_x, x, y, phase

Forward motion:
    encoder PID straight-line control

Turns:
    encoder-count based pivot_left(90)

CSV:
    encoder_only_rectangle.csv
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
CSV_PATH = REPO_ROOT / "data" / "encoder_imu_fusion" / "encoder_only_rectangle.csv"
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

WHEELBASE = 0.152
TRACK_LENGTH = 0.14
EFFECTIVE_RADIUS = math.sqrt((WHEELBASE / 2.0)**2 + (TRACK_LENGTH / 2.0)**2)
SLIP_FACTOR = 1.265

# Rectangle dimensions
RECT_LONG = 1.4
RECT_SHORT = 1.0

# ============================================================
# CONTROL
# ============================================================
DT = 0.02

# Forward PID
BASE_PWM_LEFT = 58
BASE_PWM_RIGHT = 62
PWM_MIN_FWD = 35
PWM_MAX_FWD = 100

KP_FWD = 2.0
KI_FWD = 0.2
KD_FWD = 0.3
I_CLAMP_FWD = 20.0

# Turn PID
BASE_PWM_TURN = 90
PWM_MIN_TURN = 75
PWM_MAX_TURN = 100

KP_TURN = 1.2
KI_TURN = 0.3
KD_TURN = 0.4
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
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)

last_imu_x = 0.0

def imu_x():
    global last_imu_x
    if ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        nums = re.findall(r'-?\d+\.?\d*', line)
        if len(nums) >= 1:
            last_imu_x = float(nums[0])
    return last_imu_x

def wait_for_confirmation():
    print("Waiting for IMU data. Press ENTER when heading looks correct.\n")

    while True:
        heading = imu_x()

        print(
            f"\rLive IMU_X: {heading:8.3f} deg   Press ENTER to start rectangle...",
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
    pwm1.ChangeDutyCycle(l_fwd)
    pwm2.ChangeDutyCycle(l_bwd)
    pwm4.ChangeDutyCycle(r_fwd)
    pwm3.ChangeDutyCycle(r_bwd)

def stop():
    set_motors(0, 0, 0, 0)

def drive_forward(left_duty, right_duty):
    left_duty = max(0, min(PWM_MAX_FWD, left_duty))
    right_duty = max(0, min(PWM_MAX_FWD, right_duty))
    set_motors(left_duty, 0, right_duty, 0)

def drive_pivot_left(left_duty, right_duty):
    left_duty = max(0, min(PWM_MAX_TURN, left_duty))
    right_duty = max(0, min(PWM_MAX_TURN, right_duty))
    set_motors(0, left_duty, right_duty, 0)

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
# Keep same logging / mapping logic as encoder+imu code:
# x,y are updated using latest imu_x heading
# ============================================================
def update_pose_forward(distance_m):
    global x_pos, y_pos, heading_deg
    heading_deg = imu_x()
    th = math.radians(heading_deg)
    x_pos += distance_m * math.cos(th)
    y_pos += distance_m * math.sin(th)

def update_pose_turn_left(angle_deg):
    global heading_deg
    heading_deg = (heading_deg + angle_deg) % 360.0

# ============================================================
# FORWARD WITH ENCODER FEEDBACK
# ============================================================
def forward_distance(distance_m, phase_name):
    global left_count, right_count

    reset_counts()
    target = int(distance_m / M_PER_COUNT)

    integral = 0.0
    prev_error = 0.0
    last_log = time.time()

    while left_count < target and right_count < target:
        error = left_count - right_count

        integral += error * DT
        integral = max(-I_CLAMP_FWD, min(I_CLAMP_FWD, integral))

        derivative = (error - prev_error) / DT
        prev_error = error

        correction = KP_FWD * error + KI_FWD * integral + KD_FWD * derivative

        lp = BASE_PWM_LEFT - correction
        rp = BASE_PWM_RIGHT + correction

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
# LEFT TURN WITH ENCODER FEEDBACK
# ============================================================
def pivot_left(angle_deg, phase_name):
    global left_count, right_count

    reset_counts()

    angle_rad = math.radians(angle_deg)
    arc_len = EFFECTIVE_RADIUS * angle_rad * SLIP_FACTOR
    target = int(arc_len / M_PER_COUNT)

    integral = 0.0
    prev_error = 0.0
    last_log = time.time()

    while left_count < target and right_count < target:
        error = left_count - right_count

        integral += error * DT
        integral = max(-I_CLAMP_TURN, min(I_CLAMP_TURN, integral))

        derivative = (error - prev_error) / DT
        prev_error = error

        correction = KP_TURN * error + KI_TURN * integral + KD_TURN * derivative

        lp = BASE_PWM_TURN - correction
        rp = BASE_PWM_TURN + correction

        lp = max(PWM_MIN_TURN, min(PWM_MAX_TURN, lp))
        rp = max(PWM_MIN_TURN, min(PWM_MAX_TURN, rp))

        drive_pivot_left(lp, rp)

        if time.time() - last_log >= 0.05:
            log_row(phase_name)
            last_log = time.time()

        time.sleep(DT)

    stop()
    time.sleep(0.25)

    update_pose_turn_left(angle_deg)
    log_row(f"{phase_name}_done")

# ============================================================
# MAIN
# ============================================================
enc_thread = threading.Thread(target=encoder_loop, daemon=True)
enc_thread.start()
time.sleep(0.1)

try:
    heading_deg = wait_for_confirmation()
    log_row("start")

    forward_distance(RECT_LONG, "forward_1")
    pivot_left(90, "turn_1")

    forward_distance(RECT_SHORT, "forward_2")
    pivot_left(90, "turn_2")

    forward_distance(RECT_LONG, "forward_3")
    pivot_left(90, "turn_3")

    forward_distance(RECT_SHORT, "forward_4")
    pivot_left(90, "turn_4")

    log_row("done")

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