"""
Traffic-light color contour detection on a single image.

Reads `assets/images/traffic_light.jpg`, segments by HSV for red/yellow/green,
and overlays the largest green contour with its centroid + minimum enclosing
circle.

Run from anywhere:
    python src/vision/contour_detection/contour_detection.py
"""

from pathlib import Path

import cv2 as cv
import numpy as np

# ---- repo-root-relative asset path ----
REPO_ROOT = Path(__file__).resolve().parents[3]
IMG_PATH = REPO_ROOT / "assets" / "images" / "traffic_light.jpg"

image = cv.imread(str(IMG_PATH))
if image is None:
    raise FileNotFoundError(f"Could not load image at {IMG_PATH}")
output = image.copy()

# HSV ranges
red_lower = np.array([167, 170, 40])
red_upper = np.array([179, 255, 255])
yellow_lower = np.array([20, 157, 40])
yellow_upper = np.array([40, 255, 255])
green_lower = np.array([45, 80, 70])
green_upper = np.array([95, 255, 255])

hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)

# Masks
mask_red = cv.inRange(hsv_image, red_lower, red_upper)
mask_yellow = cv.inRange(hsv_image, yellow_lower, yellow_upper)
mask_green = cv.inRange(hsv_image, green_lower, green_upper)

contours, _ = cv.findContours(mask_green, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

if len(contours) > 0:
    max_contour = max(contours, key=cv.contourArea)
    (x, y), radius = cv.minEnclosingCircle(max_contour)
    M = cv.moments(max_contour)

    cx, cy = int(x), int(y)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

    print(f"min-enclosing-circle center: ({x:.1f}, {y:.1f})  radius: {radius:.1f}")
    print(f"moment centroid:             ({cx}, {cy})")

    if radius > 10:
        # red dot at moment centroid
        cv.circle(output, (cx, cy), 4, (0, 0, 255), -1)
        # red enclosing circle around the blob
        cv.circle(output, (int(x), int(y)), int(radius), (0, 0, 255), 3)

cv.imshow("green_contour", output)
cv.waitKey(0)
cv.destroyAllWindows()
