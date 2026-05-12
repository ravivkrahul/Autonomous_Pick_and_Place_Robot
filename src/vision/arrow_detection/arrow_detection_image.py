"""
Single-image arrow direction detector (LEFT / RIGHT / UP / DOWN).

Pipeline:
    HSV mask (green)  ->  largest contour  ->  PCA principal axis  ->
    pick tip from the narrower extreme  ->  classify direction from
    (tip - centroid) angle.

Run from anywhere:
    python src/vision/arrow_detection/arrow_detection_image.py
"""

from pathlib import Path

import cv2 as cv
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
IMG_PATH = REPO_ROOT / "assets" / "images" / "arrow.JPG"

image = cv.imread(str(IMG_PATH))
if image is None:
    raise FileNotFoundError(f"Could not load image at {IMG_PATH}")

hsv = cv.cvtColor(image, cv.COLOR_BGR2HSV)

green_lower = np.array([40,80,80])
green_upper = np.array([90,255,255])

mask = cv.inRange(hsv, green_lower, green_upper)

contours,_ = cv.findContours(mask,
                             cv.RETR_EXTERNAL,
                             cv.CHAIN_APPROX_SIMPLE)

c = max(contours, key=cv.contourArea)

points = np.squeeze(c).astype(np.float64)


# -----------------------------
# centroid
# -----------------------------
centroid = np.mean(points, axis=0)

centered = points - centroid


# -----------------------------
# PCA
# -----------------------------
cov = np.dot(centered.T, centered)/(len(points)-1)

eigvals, eigvecs = np.linalg.eig(cov)

axis = eigvecs[:, np.argmax(eigvals)]

perp_axis = np.array([-axis[1], axis[0]])


# -----------------------------
# projections
# -----------------------------
proj = np.dot(centered, axis)

min_proj = np.min(proj)
max_proj = np.max(proj)


# region near extremes
threshold = 15

min_region = points[proj < min_proj + threshold]
max_region = points[proj > max_proj - threshold]


# -----------------------------
# width measurement
# -----------------------------
min_width = np.max(np.dot(min_region-centroid,perp_axis)) - \
            np.min(np.dot(min_region-centroid,perp_axis))

max_width = np.max(np.dot(max_region-centroid,perp_axis)) - \
            np.min(np.dot(max_region-centroid,perp_axis))


# -----------------------------
# tip detection
# -----------------------------
if max_width < min_width:
    tip = points[np.argmax(proj)]
else:
    tip = points[np.argmin(proj)]


tip = (int(tip[0]), int(tip[1]))

cx = int(centroid[0])
cy = int(centroid[1])


# -----------------------------
# direction
# -----------------------------
dx = tip[0] - cx
dy = tip[1] - cy

angle = np.degrees(np.arctan2(-dy, dx))

if -45 <= angle < 45:
    direction = "RIGHT"
elif 45 <= angle < 135:
    direction = "UP"
elif angle >= 135 or angle < -135:
    direction = "LEFT"
else:
    direction = "DOWN"


# -----------------------------
# visualization
# -----------------------------
cv.circle(image,(cx,cy),5,(255,0,0),-1)
cv.circle(image,tip,8,(0,0,255),-1)

cv.putText(image,direction,(40,40),
           cv.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)

cv.imshow("Arrow",image)

cv.waitKey(0)
cv.destroyAllWindows()