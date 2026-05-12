import cv2 as cv
import numpy as np
import time
from pathlib import Path
from picamera2 import Picamera2
from datetime import datetime

# Path setup: write the timing log into data/contour_detection/
REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / "data" / "contour_detection" / "recording_data.txt"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Initialize Camera
# -----------------------------
picam2 = Picamera2()
video_config = picam2.create_video_configuration(
    main={"size": (1280, 720)}
)
picam2.configure(video_config)
picam2.start()

# -----------------------------
# Green HSV Range
# -----------------------------
green_lower = np.array([45, 80, 70])
green_upper = np.array([95, 255, 255])

# -----------------------------
# Recording Variables
# -----------------------------
recording = False
record_start_time = None
record_duration = 60  # will record around 30 seconds
video_writer = None
f = open(LOG_PATH, "a")  # append-mode timing log at data/contour_detection/recording_data.txt
frame_count =0
# -----------------------------
# Main Loop
# -----------------------------
while True:
    start = datetime.now()
    # Capture frame
    image = picam2.capture_array()
    image = cv.cvtColor(image, cv.COLOR_RGB2BGR)
    output_frame = image.copy()

    # Convert to HSV
    hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)

    # Create mask
    mask_green = cv.inRange(hsv_image, green_lower, green_upper)

    # Find contours
    contours, _ = cv.findContours(
        mask_green,
        cv.RETR_EXTERNAL,
        cv.CHAIN_APPROX_SIMPLE
    )

    if len(contours) > 0:

        max_contour = max(contours, key=cv.contourArea)
        ((x, y), radius) = cv.minEnclosingCircle(max_contour)
        M = cv.moments(max_contour)

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # Draw centroid
            cv.circle(output_frame, (cx, cy), 5, (0, 0, 255), -1)

        if radius > 10:
            # Draw enclosing circle
            cv.circle(output_frame, (int(x), int(y)), int(radius), (0, 255, 0), 3)

    # Show window
    cv.imshow("Green Detection", output_frame)

    key = cv.waitKey(1) & 0xFF

    # -----------------------------
    # Quit
    # -----------------------------
    if key == ord('q'):
        break

    # -----------------------------
    # Start Recording
    # -----------------------------
    if key == ord('r') and not recording:
        print("Recording started")
        frame_count = 0 
        now = datetime.now()
        filename = now.strftime("%d-%m-%Y_%H-%M-%S") + ".mp4"

        fourcc = cv.VideoWriter_fourcc(*'mp4v')
        video_writer = cv.VideoWriter(
            filename,
            fourcc,
            15, # fps
            (1280, 720)
        )

        recording = True
        record_start_time = time.time()

    # -----------------------------
    # Write Frame if Recording
    # -----------------------------
    if recording:
        video_writer.write(output_frame)
        
        # Stop after duration
        if time.time() - record_start_time > record_duration or frame_count >= 150:
            video_writer.release()
            print("Recording saved")
            recording = False
        stop = datetime.now()
        delta = stop - start
        delta_seconds = delta.total_seconds()
        delta_ms = delta_seconds * 1000
        frame_count += 1
        print(f"Frame {frame_count}: {delta_ms:.3f} ms")
        # Save to file
        f.write(str(delta_seconds) + "\n")
# -----------------------------
# Cleanup
# -----------------------------
if recording and video_writer is not None:
    video_writer.release()
    
f.close()
cv.destroyAllWindows()
picam2.stop()