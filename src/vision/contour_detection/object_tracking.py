import cv2 as cv
import numpy as np
import time
from pathlib import Path
from picamera2 import Picamera2
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[3]
VIDEO_OUT_DIR = REPO_ROOT / "results" / "contour_detection" / "videos"
VIDEO_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Camera
picam2 = Picamera2()
video_config = picam2.create_video_configuration(
    main={"size": (1280, 720)}
)
picam2.configure(video_config)
picam2.start()


# Green HSV Range
green_lower = np.array([45, 80, 70]) # lower bound for green in HSV color space
green_upper = np.array([95, 255, 255]) # upper bound for green in HSV color space


# Recording Variables
recording = False
record_start_time = None
record_duration = 60  # will record around 30 seconds
video_writer = None


# Main Loop
while True:

    # Capture frame
    image = picam2.capture_array()
    image = cv.cvtColor(image, cv.COLOR_RGB2BGR)
    # Convert from RGB to BGR color space for OpenCV processing 
    # because OpenCV uses BGR by default and PiCamera2 captures in RGB format. 
    # This conversion ensures that the colors are correctly interpreted
    # when processing the image with OpenCV functions.
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
# The cv.findContours function is used to find contours in the binary mask created by cv.inRange. 
# It retrieves the contours and their hierarchy. The contours are stored as a list of points that define the shape of the detected objects in the mask. 
# The hierarchy provides information about the relationship between contours (e.g., which contours are nested within others).

    if len(contours) > 0:

        max_contour = max(contours, key=cv.contourArea)
# Find the contour with the largest area, which is likely to correspond to the most prominent green object in the frame.

        ((x, y), radius) = cv.minEnclosingCircle(max_contour)
# Calculate the minimum enclosing circle for the largest contour, which gives the center (x, y) and radius of the circle that can enclose the contour.
        M = cv.moments(max_contour)
# The cv.moments function calculates spatial moments of the contour, which are used to compute properties like the centroid.

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
# here M["m00"] represents the area of the contour. If it's not zero, we can calculate the centroid (cx, cy) using the moments.
# The centroid is calculated as (M["m10"] / M["m00"], M["m01"] / M["m00"]), where M["m10"] and M["m01"] are the first-order moments of the contour.

            # Draw centroid
            cv.circle(output_frame, (cx, cy), 5, (0, 0, 255), -1)

        if radius > 10:
            # Draw enclosing circle
            cv.circle(output_frame, (int(x), int(y)), int(radius), (0, 255, 0), 3)

    # Show window for live preview
    cv.imshow("Green Detection", output_frame)

    key = cv.waitKey(1) & 0xFF

    # Quit on 'q'
    if key == ord('q'):
        break

    # Start Recording on press 'r'
    #ord returns the ASCII value of the character 'r', which is 114.
    # The condition checks if the 'r' key is pressed and if recording is not already in progress.
   
    if key == ord('r') and not recording:
        print("Recording started")

        now = datetime.now()
        filename = str(VIDEO_OUT_DIR / (now.strftime("%d-%m-%Y_%H-%M-%S") + ".mp4"))

        fourcc = cv.VideoWriter_fourcc(*'mp4v')
        video_writer = cv.VideoWriter(
            filename,
            fourcc,
            15, # fps
            (1280, 720)
        )

        recording = True
        record_start_time = time.time()

    
    # Write Frame if Recording
    if recording:
        video_writer.write(output_frame)

        # Stop after duration
        if time.time() - record_start_time > record_duration:
            video_writer.release()
            print("Recording saved")
            recording = False

# Cleanup
if recording and video_writer is not None:
    video_writer.release()

cv.destroyAllWindows()
picam2.stop()