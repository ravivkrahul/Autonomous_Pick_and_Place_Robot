import cv2
from picamera2 import Picamera2
from datetime import datetime

picam2= Picamera2()

picam2.preview_configuration.main.size=(1280, 720) #720 p HD resolution
picam2.preview_configuration.main.format="RGB888" # format for opencv 24 bits per pixel
picam2.preview_configuration.align() # align the configuration to the camera's requirements
picam2.configure("preview")
# Applies preview configuration
# Puts camera into preview mode
# Optimized for real-time display (not high-quality still capture)
picam2.start()

try:
    while True:
        now=datetime.now()
        today=now.strftime("%d-%m-%Y_%H-%M-%S")
        
        image=picam2.capture_array()
        
        cv2.imshow("Camera", image)
        key=cv2.waitKey(1) & 0xFF
        if key==ord("s"):
            cv2.imwrite(today+".jpg", image)
            print(today)
            print("Image Saved")
        
        elif key==ord("q"):
            break
finally:
    picam2.stop()
    cv2.destroyAllWindows()
    