#!/usr/bin/env python3
"""
Centering tuning script for ENPM701 robot.

Purpose:
- Tune object centering BEFORE running full mission.
- Detect selected color block.
- Show live camera + mask.
- Print pixel error from image center.
- Optional motor centering test:
    - Press 'm' to enable/disable motor centering.
    - Press 's' to stop motors.
    - Press 'q' to quit.

Controls:
    r / g / b : change target color
    m         : toggle motor centering ON/OFF
    s         : stop motors immediately
    q         : quit

Tuning parameters to adjust:
    CENTER_KP
    CENTER_KD
    CENTER_PID_MIN_PWM
    CENTER_PID_MAX_PWM
    PIXEL_TOLERANCE

If robot overshoots center:
    - reduce CENTER_KP
    - reduce CENTER_PID_MIN_PWM
    - increase CENTER_KD slightly

If robot is too slow / does not move:
    - increase CENTER_PID_MIN_PWM
    - increase CENTER_KP

If robot jitters around center:
    - increase PIXEL_TOLERANCE
    - reduce CENTER_KP
    - increase CENTER_KD slightly
"""

import cv2
import numpy as np
from picamera2 import Picamera2
import RPi.GPIO as GPIO
import time

# ==========================================================
# GPIO / MOTOR PINS
# ==========================================================
IN1, IN2, IN3, IN4 = 6, 13, 19, 26
PWM_FREQ = 1000

# ==========================================================
# CAMERA
# ==========================================================
WIDTH = 640
HEIGHT = 480
CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

# ==========================================================
# DETECTION
# ==========================================================
MIN_CONTOUR_AREA = 150

# ==========================================================
# CENTERING TUNING PARAMETERS
# ==========================================================
CENTER_KP = 0.22
CENTER_KI = 5
CENTER_KD = 0.0

CENTER_PID_MIN_PWM = 40
CENTER_PID_MAX_PWM = 70

PIXEL_TOLERANCE = 10

# Optional safety: if object error is huge, use max PWM but still bounded.
MAX_PIXEL_ERROR_FOR_DISPLAY = 320

# ==========================================================
# GPIO SETUP
# ==========================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

pwm1 = GPIO.PWM(IN1, PWM_FREQ)
pwm2 = GPIO.PWM(IN2, PWM_FREQ)
pwm3 = GPIO.PWM(IN3, PWM_FREQ)
pwm4 = GPIO.PWM(IN4, PWM_FREQ)

for p in [pwm1, pwm2, pwm3, pwm4]:
    p.start(0)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def set_motors(l_fwd, l_bwd, r_fwd, r_bwd):
    pwm1.ChangeDutyCycle(clamp(l_fwd, 0, 100))
    pwm2.ChangeDutyCycle(clamp(l_bwd, 0, 100))
    pwm4.ChangeDutyCycle(clamp(r_fwd, 0, 100))
    pwm3.ChangeDutyCycle(clamp(r_bwd, 0, 100))

def stop():
    set_motors(0, 0, 0, 0)

def pivot_right_pwm(pwm):
    set_motors(pwm, 0, 0, pwm)

def pivot_left_pwm(pwm):
    set_motors(0, pwm, pwm, 0)

# ==========================================================
# PID
# ==========================================================
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def compute(self, error):
        now = time.time()
        dt = 0.0 if self.prev_time is None else now - self.prev_time
        self.prev_time = now

        if dt > 0:
            self.integral += error * dt
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0

        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

center_pid = PID(CENTER_KP, CENTER_KI, CENTER_KD)

# ==========================================================
# VISION
# ==========================================================
def get_mask(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    if color == "red":
        # Current tuned red mask from main robot code
        m1 = cv2.inRange(hsv, np.array([0, 175, 119]), np.array([10, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([164, 89, 80]), np.array([180, 255, 255]))
        mask = m1 | m2

    elif color == "green":
        mask = cv2.inRange(hsv, np.array([50, 170, 110]), np.array([100, 255, 255]))

    elif color == "blue":
        mask = cv2.inRange(hsv, np.array([95, 239, 108]), np.array([130, 255, 255]))

    else:
        mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

    k = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, k, iterations=1)
    mask = cv2.dilate(mask, k, iterations=2)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    return mask

def detect_object(frame, color):
    mask = get_mask(frame, color)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, mask

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)

    if area < MIN_CONTOUR_AREA:
        return None, mask

    M = cv2.moments(contour)
    if M["m00"] == 0:
        return None, mask

    x, y, w, h = cv2.boundingRect(contour)
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return {
        "x": x, "y": y, "w": w, "h": h,
        "cx": cx, "cy": cy,
        "area": area,
        "contour": contour,
        "color": color,
    }, mask

def draw_debug(debug, mask, obj, color, motor_enabled, last_pwm, last_action):
    cv2.line(debug, (CENTER_X, 0), (CENTER_X, HEIGHT), (0, 255, 0), 1)
    cv2.line(debug, (0, CENTER_Y), (WIDTH, CENTER_Y), (0, 255, 0), 1)

    cv2.putText(debug, f"TARGET: {color.upper()}  MOTOR: {'ON' if motor_enabled else 'OFF'}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    cv2.putText(debug, f"KP={CENTER_KP:.2f} KD={CENTER_KD:.2f} MIN={CENTER_PID_MIN_PWM} MAX={CENTER_PID_MAX_PWM} TOL={PIXEL_TOLERANCE}",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

    if obj is not None:
        x, y, w, h = obj["x"], obj["y"], obj["w"], obj["h"]
        cx, cy = obj["cx"], obj["cy"]
        error = cx - CENTER_X

        color_bgr = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
        }.get(color, (255, 255, 255))

        cv2.rectangle(debug, (x, y), (x + w, y + h), color_bgr, 2)
        cv2.circle(debug, (cx, cy), 5, color_bgr, -1)
        cv2.line(debug, (CENTER_X, CENTER_Y), (cx, cy), (255, 255, 0), 2)
        cv2.drawContours(debug, [obj["contour"]], -1, (255, 0, 255), 2)

        status = "CENTERED" if abs(error) <= PIXEL_TOLERANCE else "CENTERING"
        cv2.putText(debug, f"err={error:+d}px area={obj['area']:.0f} h={h}px {status}",
                    (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

        cv2.putText(debug, f"action={last_action} pwm={last_pwm:.1f}",
                    (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

        # Error bar
        bar_x1, bar_y = 160, 455
        bar_w = 320
        cv2.rectangle(debug, (bar_x1, bar_y - 10), (bar_x1 + bar_w, bar_y + 10), (120, 120, 120), 1)
        center_bar = bar_x1 + bar_w // 2
        cv2.line(debug, (center_bar, bar_y - 15), (center_bar, bar_y + 15), (0, 255, 0), 2)
        err_clamped = int(clamp(error, -MAX_PIXEL_ERROR_FOR_DISPLAY, MAX_PIXEL_ERROR_FOR_DISPLAY))
        marker_x = int(center_bar + (err_clamped / MAX_PIXEL_ERROR_FOR_DISPLAY) * (bar_w // 2))
        cv2.circle(debug, (marker_x, bar_y), 7, (0, 255, 255), -1)

    else:
        cv2.putText(debug, "NO OBJECT DETECTED",
                    (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

    masked_preview = cv2.bitwise_and(debug, debug, mask=mask)
    return masked_preview

def centering_step(obj, motor_enabled):
    """One control step for pivot centering."""
    if obj is None:
        stop()
        center_pid.reset()
        return 0.0, "NO_OBJECT"

    error = obj["cx"] - CENTER_X

    if abs(error) <= PIXEL_TOLERANCE:
        stop()
        center_pid.reset()
        return 0.0, "CENTERED"

    control = center_pid.compute(error)
    turn_pwm = clamp(abs(control), CENTER_PID_MIN_PWM, CENTER_PID_MAX_PWM)

    if motor_enabled:
        if error > 0:
            pivot_right_pwm(turn_pwm)
            return turn_pwm, "PIVOT_RIGHT"
        else:
            pivot_left_pwm(turn_pwm)
            return turn_pwm, "PIVOT_LEFT"
    else:
        stop()
        return turn_pwm, "MOTOR_OFF"

def main():
    global center_pid

    target_color = "red"
    motor_enabled = False
    last_pwm = 0.0
    last_action = "INIT"

    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (WIDTH, HEIGHT)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    time.sleep(2)

    print("\n=== CENTERING TUNING SCRIPT ===")
    print("r/g/b : select color")
    print("m     : toggle motor centering ON/OFF")
    print("s     : stop motors")
    print("q     : quit")
    print("\nStart with MOTOR OFF and confirm detection/err sign first.")
    print("Then press m to enable motor centering.\n")

    try:
        while True:
            frame = picam2.capture_array()
            debug = frame.copy()

            obj, mask = detect_object(frame, target_color)

            last_pwm, last_action = centering_step(obj, motor_enabled)

            masked_preview = draw_debug(debug, mask, obj, target_color,
                                        motor_enabled, last_pwm, last_action)

            # cv2.imshow("Centering Tune - Camera", debug)
            # cv2.imshow("Centering Tune - Mask", mask)
            cv2.imshow("Centering Tune - Masked Preview", masked_preview)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            elif key == ord("s"):
                motor_enabled = False
                stop()
                center_pid.reset()
                print("[STOP] Motors stopped.")

            elif key == ord("m"):
                motor_enabled = not motor_enabled
                stop()
                center_pid.reset()
                print(f"[MOTOR] Centering motor {'ENABLED' if motor_enabled else 'DISABLED'}")

            elif key == ord("r"):
                target_color = "red"
                stop()
                center_pid.reset()
                print("[COLOR] RED")

            elif key == ord("g"):
                target_color = "green"
                stop()
                center_pid.reset()
                print("[COLOR] GREEN")

            elif key == ord("b"):
                target_color = "blue"
                stop()
                center_pid.reset()
                print("[COLOR] BLUE")

            time.sleep(0.01)

    finally:
        stop()
        time.sleep(0.2)
        picam2.stop()
        cv2.destroyAllWindows()

        for p in [pwm1, pwm2, pwm3, pwm4]:
            p.stop()

        GPIO.cleanup()
        print("Done.")

if __name__ == "__main__":
    main()
