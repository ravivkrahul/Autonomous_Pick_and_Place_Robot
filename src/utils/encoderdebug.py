#!/usr/bin/env python3
"""
Encoder debug WITHOUT interrupts (polling based)

Controls:
  w = forward
  s = backward
  a = turn left
  d = turn right
  space = stop
  r = reset counts
  x = quit
"""

import RPi.GPIO as GPIO
import sys
import tty
import termios
import time
import threading

# ---------------- Pins ----------------
IN1 = 6
IN2 = 13
IN3 = 19
IN4 = 26

ENC_RIGHT = 18
ENC_LEFT = 4

# ---------------- Setup ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(ENC_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ENC_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ---------------- PWM ----------------
pwm1 = GPIO.PWM(IN1, 1000)
pwm2 = GPIO.PWM(IN2, 1000)
pwm3 = GPIO.PWM(IN3, 1000)
pwm4 = GPIO.PWM(IN4, 1000)

pwm1.start(0)
pwm2.start(0)
pwm3.start(0)
pwm4.start(0)

LEFT_SPEED = 60
RIGHT_SPEED = 60

# ---------------- Encoder State ----------------
left_count = 0
right_count = 0
running = True

prev_left = 0
prev_right = 0

# ---------------- Encoder Polling ----------------
def encoder_loop():
    global left_count, right_count, prev_left, prev_right

    while running:
        curr_left = GPIO.input(ENC_LEFT)
        curr_right = GPIO.input(ENC_RIGHT)

        # Rising edge detection
        if prev_left == 0 and curr_left == 1:
            left_count += 1

        if prev_right == 0 and curr_right == 1:
            right_count += 1

        prev_left = curr_left
        prev_right = curr_right

        # small delay to avoid CPU overload
        time.sleep(0.001)   # 1 ms

# ---------------- Motor Control ----------------
def set_motors(l_fwd, l_bwd, r_fwd, r_bwd):
    pwm1.ChangeDutyCycle(l_fwd)
    pwm2.ChangeDutyCycle(l_bwd)
    pwm4.ChangeDutyCycle(r_fwd)   # right motor inverted
    pwm3.ChangeDutyCycle(r_bwd)

def stop():
    set_motors(0, 0, 0, 0)

def forward():
    set_motors(LEFT_SPEED, 0, RIGHT_SPEED, 0)

def backward():
    set_motors(0, LEFT_SPEED, 0, RIGHT_SPEED)

def turn_left():
    set_motors(0, 0, RIGHT_SPEED, 0)

def turn_right():
    set_motors(LEFT_SPEED, 0, 0, 0)

def reset_counts():
    global left_count, right_count
    left_count = 0
    right_count = 0

# ---------------- Keyboard ----------------
def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

# ---------------- Display ----------------
def display_loop():
    global running
    while running:
        diff = left_count - right_count
        sys.stdout.write(f"\rL:{left_count:5d}   R:{right_count:5d}   Diff:{diff:+5d}   ")
        sys.stdout.flush()
        time.sleep(0.1)

# ---------------- Main ----------------
print("=" * 50)
print("ENCODER DEBUG (POLLING - NO INTERRUPTS)")
print("=" * 50)

# Start threads
threading.Thread(target=encoder_loop, daemon=True).start()
threading.Thread(target=display_loop, daemon=True).start()

try:
    while True:
        key = get_key().lower()

        if key == 'w':
            forward()
        elif key == 's':
            backward()
        elif key == 'a':
            turn_left()
        elif key == 'd':
            turn_right()
        elif key == ' ':
            stop()
        elif key == 'r':
            reset_counts()
        elif key == 'x':
            break

except KeyboardInterrupt:
    pass

finally:
    running = False
    stop()
    pwm1.stop()
    pwm2.stop()
    pwm3.stop()
    pwm4.stop()
    GPIO.cleanup()
    print("\nClean exit.")