#!/usr/bin/env python3
"""Gripper sweep: close → open → close, 2s pause between steps."""

import RPi.GPIO as GPIO
import time

SERVO_PIN = 16
GRIP_MIN = 7.2   # closed
GRIP_MAX = 11.5  # open
STEP = GRIP_MAX - GRIP_MIN
STEP /= 5  # 5 steps for full range

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

# Build duty list: close → open → close
duties_open  = [GRIP_MIN + STEP * i for i in range(6)]
duties_close = [GRIP_MAX - STEP * i for i in range(1, 6)]
duties = duties_open + duties_close

try:
    for i, duty in enumerate(duties):
        pwm.ChangeDutyCycle(duty)
        time.sleep(1.0)
        pwm.ChangeDutyCycle(0)
        print(f"  [{i+1:2d}/{len(duties)}] duty={duty:.2f}%")
        time.sleep(2.0)
finally:
    pwm.stop()
    GPIO.cleanup()
    print("Done.")