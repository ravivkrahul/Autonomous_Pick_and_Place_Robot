#!/usr/bin/env python3

import cv2
import numpy as np
from picamera2 import Picamera2
import time

WIDTH = 640
HEIGHT = 480

def nothing(x):
    pass

def main():
    cv2.namedWindow("Trackbars", cv2.WINDOW_NORMAL)

    cv2.createTrackbar("H_MIN", "Trackbars", 0, 180, nothing)
    cv2.createTrackbar("S_MIN", "Trackbars", 0, 255, nothing)
    cv2.createTrackbar("V_MIN", "Trackbars", 0, 255, nothing)

    cv2.createTrackbar("H_MAX", "Trackbars", 180, 180, nothing)
    cv2.createTrackbar("S_MAX", "Trackbars", 255, 255, nothing)
    cv2.createTrackbar("V_MAX", "Trackbars", 255, 255, nothing)

    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (WIDTH, HEIGHT)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    time.sleep(2)

    print("Live HSV tuner started.")
    print("Press q to quit.")
    print("Press p to print current HSV values.")

    try:
        while True:
            frame = picam2.capture_array()

            # Keep this same as your robot code
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            h_min = cv2.getTrackbarPos("H_MIN", "Trackbars")
            s_min = cv2.getTrackbarPos("S_MIN", "Trackbars")
            v_min = cv2.getTrackbarPos("V_MIN", "Trackbars")

            h_max = cv2.getTrackbarPos("H_MAX", "Trackbars")
            s_max = cv2.getTrackbarPos("S_MAX", "Trackbars")
            v_max = cv2.getTrackbarPos("V_MAX", "Trackbars")

            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])

            mask = cv2.inRange(hsv, lower, upper)

            kernel = np.ones((5, 5), np.uint8)
            mask_clean = cv2.erode(mask, kernel, iterations=1)
            mask_clean = cv2.dilate(mask_clean, kernel, iterations=2)
            mask_clean = cv2.GaussianBlur(mask_clean, (5, 5), 0)

            preview = cv2.bitwise_and(frame, frame, mask=mask_clean)

            cv2.imshow("Live Camera", frame)
            cv2.imshow("Mask", mask_clean)
            cv2.imshow("Masked Preview", preview)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord("p"):
                print()
                print(f"mask = cv2.inRange(hsv, np.array([{h_min}, {s_min}, {v_min}]), np.array([{h_max}, {s_max}, {v_max}]))")
                print()
            # Put this inside the while True loop, after key = cv2.waitKey(1) & 0xFF

            if key == ord("r"):
                cv2.setTrackbarPos("H_MIN", "Trackbars", 0)
                cv2.setTrackbarPos("S_MIN", "Trackbars", 175)
                cv2.setTrackbarPos("V_MIN", "Trackbars", 70)

                cv2.setTrackbarPos("H_MAX", "Trackbars", 10)
                cv2.setTrackbarPos("S_MAX", "Trackbars", 255)
                cv2.setTrackbarPos("V_MAX", "Trackbars", 255)

            elif key == ord("g"):
                cv2.setTrackbarPos("H_MIN", "Trackbars", 50)
                cv2.setTrackbarPos("S_MIN", "Trackbars", 170)
                cv2.setTrackbarPos("V_MIN", "Trackbars", 110)

                cv2.setTrackbarPos("H_MAX", "Trackbars", 100)
                cv2.setTrackbarPos("S_MAX", "Trackbars", 255)
                cv2.setTrackbarPos("V_MAX", "Trackbars", 255)

            elif key == ord("b"):
                cv2.setTrackbarPos("H_MIN", "Trackbars", 95)
                cv2.setTrackbarPos("S_MIN", "Trackbars", 180)
                cv2.setTrackbarPos("V_MIN", "Trackbars", 120)

                cv2.setTrackbarPos("H_MAX", "Trackbars", 130)
                cv2.setTrackbarPos("S_MAX", "Trackbars", 255)
                cv2.setTrackbarPos("V_MAX", "Trackbars", 255)
    finally:
        picam2.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()