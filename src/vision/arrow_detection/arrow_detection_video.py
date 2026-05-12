import cv2 as cv
import numpy as np
import time
from pathlib import Path
from picamera2 import Picamera2
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / "data" / "arrow_detection" / "hw4_recording_data.txt"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
VIDEO_OUT_DIR = REPO_ROOT / "results" / "arrow_detection" / "videos"
VIDEO_OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Initialize camera
# -----------------------------
picam2 = Picamera2()

video_config = picam2.create_video_configuration(
    main={"size": (1280,720)}
)

picam2.configure(video_config)
picam2.start()


# -----------------------------
# HSV range
# -----------------------------
green_lower = np.array([40,80,80])
green_upper = np.array([90,255,255])


# -----------------------------
# Recording variables
# -----------------------------
recording = False
video_writer = None
frame_count = 0

f = open(LOG_PATH, "a")


# -----------------------------
# Direction classification
# -----------------------------
def classify_direction(dx,dy):

    angle = np.degrees(np.arctan2(-dy,dx))

    if -45 <= angle < 45:
        return "RIGHT"
    elif 45 <= angle < 135:
        return "UP"
    elif angle >= 135 or angle < -135:
        return "LEFT"
    else:
        return "DOWN"


# -----------------------------
# Main loop
# -----------------------------
while True:

    start = datetime.now()

    frame = picam2.capture_array()
    frame = cv.cvtColor(frame, cv.COLOR_RGB2BGR)

    output = frame.copy()


    # -----------------------------
    # HSV segmentation
    # -----------------------------
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

    mask = cv.inRange(hsv, green_lower, green_upper)


    # -----------------------------
    # Contours
    # -----------------------------
    contours,_ = cv.findContours(mask,
                                 cv.RETR_EXTERNAL,
                                 cv.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:

        c = max(contours, key=cv.contourArea)

        if cv.contourArea(c) > 500:

            points = np.squeeze(c).astype(np.float64)

            if len(points) > 5:

                centroid = np.mean(points, axis=0)
                centered = points - centroid

                cov = np.dot(centered.T, centered)/(len(points)-1)

                eigvals, eigvecs = np.linalg.eig(cov)

                axis = eigvecs[:, np.argmax(eigvals)]

                perp_axis = np.array([-axis[1], axis[0]])

                proj = np.dot(centered, axis)

                min_proj = np.min(proj)
                max_proj = np.max(proj)

                threshold = 15

                min_region = points[proj < min_proj + threshold]
                max_region = points[proj > max_proj - threshold]

                if len(min_region) > 0 and len(max_region) > 0:

                    min_width = np.max(np.dot(min_region-centroid,perp_axis)) - \
                                np.min(np.dot(min_region-centroid,perp_axis))

                    max_width = np.max(np.dot(max_region-centroid,perp_axis)) - \
                                np.min(np.dot(max_region-centroid,perp_axis))

                    if max_width < min_width:
                        tip = points[np.argmax(proj)]
                    else:
                        tip = points[np.argmin(proj)]

                    tip = (int(tip[0]), int(tip[1]))

                    cx = int(centroid[0])
                    cy = int(centroid[1])

                    dx = tip[0] - cx
                    dy = tip[1] - cy

                    direction = classify_direction(dx,dy)

                    cv.drawContours(output,[c],-1,(255,0,0),2)
                    cv.circle(output,(cx,cy),5,(255,0,0),-1)
                    cv.circle(output,tip,8,(0,0,255),-1)

                    cv.putText(output,direction,(40,40),
                               cv.FONT_HERSHEY_SIMPLEX,
                               1,(0,255,0),2)


    # -----------------------------
    # Frame timing
    # -----------------------------
    stop = datetime.now()

    delta = stop - start
    delta_seconds = delta.total_seconds()
    delta_ms = delta_seconds * 1000


    # -----------------------------
    # If recording → save timing + frame
    # -----------------------------
    if recording:

        frame_count += 1

        print(f"Frame {frame_count}: {delta_ms:.3f} ms")

        f.write(str(delta_seconds) + "\n")

        video_writer.write(output)


    cv.imshow("Arrow Detection", output)


    key = cv.waitKey(1) & 0xFF


    # -----------------------------
    # Start recording
    # -----------------------------
    if key == ord('r') and not recording:

        print("Recording started")

        frame_count = 0

        now = datetime.now()
        filename = str(VIDEO_OUT_DIR / (now.strftime("%d-%m-%Y_%H-%M-%S") + ".mp4"))

        fourcc = cv.VideoWriter_fourcc(*'mp4v')

        video_writer = cv.VideoWriter(
            filename,
            fourcc,
            15,
            (1280,720)
        )

        recording = True


    # -----------------------------
    # Stop recording
    # -----------------------------
    if key == ord('s') and recording:

        video_writer.release()
        recording = False

        print("Recording stopped")


    # -----------------------------
    # Quit program
    # -----------------------------
    if key == ord('q'):

        if recording and video_writer is not None:
            video_writer.release()

        break


# -----------------------------
# Cleanup
# -----------------------------
f.close()

cv.destroyAllWindows()

picam2.stop()