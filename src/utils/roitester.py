import cv2
import numpy as np
from picamera2 import Picamera2
import time

# =========================
# CAMERA SETUP
# =========================
WIDTH, HEIGHT = 640, 480
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2

picam2 = Picamera2()
picam2.preview_configuration.main.size = (WIDTH, HEIGHT)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

time.sleep(2)

# =========================
# ROI SETTINGS (TUNE THESE)
# =========================
ROI_W = 260
ROI_H = 140

# Move ROI if needed
ROI_OFFSET_X = 0     # + right, - left
ROI_OFFSET_Y = 0     # + up, - down

TARGET_COLOR = "red"

# =========================
# COLOR MASK (same as yours)
# =========================
def get_mask(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    if color == "red":
        m1 = cv2.inRange(hsv, np.array([0, 187, 40]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([171, 147, 88]), np.array([180, 255, 255]))
        mask = m1 | m2

    elif color == "green":
        mask = cv2.inRange(hsv, np.array([43, 170, 110]), np.array([89, 255, 255]))

    elif color == "blue":
        mask = cv2.inRange(hsv, np.array([95, 180, 120]), np.array([150, 255, 255]))

    k = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, k, iterations=1)
    mask = cv2.dilate(mask, k, iterations=2)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    return mask

# =========================
# MAIN LOOP
# =========================
while True:
    frame = picam2.capture_array()
    debug = frame.copy()

    mask = get_mask(frame, TARGET_COLOR)

    # ROI calculation
    x1 = CENTER_X - ROI_W // 2 + ROI_OFFSET_X
    x2 = CENTER_X + ROI_W // 2 + ROI_OFFSET_X
    y1 = HEIGHT - ROI_H - ROI_OFFSET_Y
    y2 = HEIGHT - ROI_OFFSET_Y

    roi = mask[y1:y2, x1:x2]

    color_pixels = int(cv2.countNonZero(roi))
    roi_area = ROI_W * ROI_H
    ratio = color_pixels / roi_area

    # Draw ROI box
    cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Draw center lines
    cv2.line(debug, (CENTER_X, 0), (CENTER_X, HEIGHT), (255, 255, 0), 1)
    cv2.line(debug, (0, CENTER_Y), (WIDTH, CENTER_Y), (255, 255, 0), 1)

    # Text info
    cv2.putText(debug, f"Pixels: {color_pixels}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    cv2.putText(debug, f"Ratio: {ratio:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    cv2.putText(debug, f"ROI W:{ROI_W} H:{ROI_H}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    cv2.putText(debug, f"Offset X:{ROI_OFFSET_X} Y:{ROI_OFFSET_Y}", (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    # Show windows
    cv2.imshow("ROI Debug", debug)
    cv2.imshow("Mask", mask)

    key = cv2.waitKey(1) & 0xFF

    # =========================
    # CONTROLS (LIVE TUNING)
    # =========================
    if key == ord('q'):
        print("\n===== FINAL ROI VALUES =====")
        print(f"ROI_W = {ROI_W}")
        print(f"ROI_H = {ROI_H}")
        print(f"ROI_OFFSET_X = {ROI_OFFSET_X}")
        print(f"ROI_OFFSET_Y = {ROI_OFFSET_Y}")
        print("================================\n")
        break

    elif key == ord('w'):
        ROI_OFFSET_Y -= 5   # move up
    elif key == ord('s'):
        ROI_OFFSET_Y += 5   # move down

    elif key == ord('a'):
        ROI_OFFSET_X -= 5   # move left
    elif key == ord('d'):
        ROI_OFFSET_X += 5   # move right

    elif key == ord('i'):
        ROI_H += 10
    elif key == ord('k'):
        ROI_H -= 10

    elif key == ord('j'):
        ROI_W -= 10
    elif key == ord('l'):
        ROI_W += 10

# Cleanup
cv2.destroyAllWindows()
picam2.stop()