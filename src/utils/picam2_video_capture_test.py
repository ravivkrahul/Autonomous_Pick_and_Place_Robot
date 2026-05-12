import cv2
import time
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from datetime import datetime

picam2 = Picamera2()

video_config = picam2.create_video_configuration(
    main={"size": (1280, 720)}
)
picam2.configure(video_config)
picam2.start()

encoder = H264Encoder(bitrate=10000000)

print("Press 'r' to start recording (10 sec delay). Press 'q' to quit.")

try:
    while True:
        frame = picam2.capture_array()
        cv2.imshow("Camera Preview", frame)

        key = cv2.waitKey(1) & 0xFF

        # Start recording
        if key == ord('r'):
            print("Recording will start in 10 seconds...")
            
            for i in range(10, 0, -1):
                print(f"Starting in {i}...")
                time.sleep(1)

            now = datetime.now()
            filename = now.strftime("%d-%m-%Y_%H-%M-%S") + ".mp4"
            output = FfmpegOutput(filename)

            print("Recording started!")
            picam2.start_recording(encoder, output)

            time.sleep(15)  # record for 15 seconds

            picam2.stop_recording()
            print("Recording saved as:", filename)

        # Quit
        elif key == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()