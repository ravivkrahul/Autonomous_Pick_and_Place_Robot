import cv2
from pyzbar.pyzbar import decode
from picamera2 import Picamera2

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

while True:
    frame = picam2.capture_array()

    decoded_objects = decode(frame)

    for obj in decoded_objects:
        print("Decoded:", obj.data.decode())

    cv2.imshow("QR Scanner", frame)

    if cv2.waitKey(1) == ord("q"):
        break