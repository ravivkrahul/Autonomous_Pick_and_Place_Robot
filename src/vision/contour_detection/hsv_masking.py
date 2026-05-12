"""
Side-by-side HSV pipeline visualization for the traffic-light image.

Stacks [original | HSV | red mask | red applied | yellow mask | yellow applied
| green mask | green applied] for a quick visual check of the HSV ranges.

Run from anywhere:
    python src/vision/contour_detection/hsv_masking.py
"""

from pathlib import Path

import cv2 as cv
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
IMG_PATH = REPO_ROOT / "assets" / "images" / "traffic_light.jpg"

image = cv.imread(str(IMG_PATH))
if image is None:
    raise FileNotFoundError(f"Could not load image at {IMG_PATH}")

red_lower = np.array([160, 80, 40])
red_upper = np.array([179, 255, 255])
yellow_lower = np.array([20, 157, 40])
yellow_upper = np.array([40, 255, 255])
green_lower = np.array([45, 80, 70])
green_upper = np.array([95, 255, 255])

hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)

# masks
mask_red = cv.inRange(hsv_image, red_lower, red_upper)
mask_yellow = cv.inRange(hsv_image, yellow_lower, yellow_upper)
mask_green = cv.inRange(hsv_image, green_lower, green_upper)

# Images after applying mask
red_image = cv.bitwise_and(image, image, mask=mask_red)
yellow_image = cv.bitwise_and(image, image, mask=mask_yellow)
green_image = cv.bitwise_and(image, image, mask=mask_green)

# Converting to same color channels for stacking
hsv_display = cv.cvtColor(hsv_image, cv.COLOR_HSV2BGR)
mask_red_3 = cv.cvtColor(mask_red, cv.COLOR_GRAY2BGR)
mask_yellow_3 = cv.cvtColor(mask_yellow, cv.COLOR_GRAY2BGR)
mask_green_3 = cv.cvtColor(mask_green, cv.COLOR_GRAY2BGR)

# Stack
stacked = np.hstack((
    image,
    hsv_image,
    mask_red_3,
    red_image,
    mask_yellow_3,
    yellow_image,
    mask_green_3,
    green_image
))

cv.imshow('All Outputs | HSV ', stacked)
cv.waitKey(0)
cv.destroyAllWindows()