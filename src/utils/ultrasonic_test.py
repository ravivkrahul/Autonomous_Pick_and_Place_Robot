#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time

TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, GPIO.LOW)

print("Ultrasonic sensor test — hold objects in front of sensor")
print("Press Ctrl+C to stop\n")
time.sleep(0.5)

def measure():
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    timeout = time.time() + 0.04
    start = time.time()
    while GPIO.input(ECHO) == 0:
        start = time.time()
        if start > timeout:
            return -1

    timeout = time.time() + 0.04
    end = time.time()
    while GPIO.input(ECHO) == 1:
        end = time.time()
        if end > timeout:
            return -1

    distance_cm = (end - start) * 17150
    return round(distance_cm, 2)

try:
    while True:
        d = measure()
        if d < 0:
            print("  Timeout — no echo received")
        else:
            print(f"  Distance: {d:6.1f} cm")
        time.sleep(0.3)
except KeyboardInterrupt:
    print("\nDone.")
finally:
    GPIO.cleanup()
