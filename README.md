# Autonomous Pick and Place Robot

## Youtube : https://www.youtube.com/playlist?list=PLdM7LpLw5C1EBv95E1sSbJ2eZQ9Ftlzfo

End-to-end build of a small autonomous ground robot — perception, localization, and low-level control — on a **Raspberry Pi 4 + PiCamera 2 + Arduino Nano (BNO055 IMU)** stack. Built for the ENPM 701 robot platform at the University of Maryland.

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20OS%20Bookworm-c51a4a.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## What's in here

| Subsystem | Highlight |
|---|---|
| **Vision** | HSV color segmentation, contour-based object tracking, arrow direction detection via PCA, traffic-light detection |
| **Localization** | Wheel-encoder dead reckoning vs. encoder + IMU yaw fusion on a closed rectangular path |
| **Low-level control** | PID heading-hold during straight motion, encoder-based pivot turns, gripper servo, ultrasonic obstacle sensing |
| **Hardware bring-up** | Serial-from-Nano IMU pipeline, PiCam2 image/video capture, QR-code decoding, GPIO cleanup |

---

## Results

### Encoder-only vs. encoder + IMU fusion (rectangular path)

Both runs follow the same commanded rectangle (1.4 m × 1.0 m, four 90° left pivots). The encoder-only path accumulates heading drift on each turn; fusing IMU yaw closes the loop visibly tighter.

| Encoder only | Encoder + IMU yaw fusion |
|---|---|
| ![encoder only](results/encoder_imu_fusion/encoder_only.png) | ![encoder + IMU](results/encoder_imu_fusion/imu_encoder.png) |

Raw trajectory CSVs are in [`data/encoder_imu_fusion/`](data/encoder_imu_fusion/).

### Traffic-light HSV pipeline

![hsv pipeline](results/contour_detection/images/hsv_pipeline.png)

Source: `assets/images/traffic_light.jpg` → HSV split into red / yellow / green masks → largest contour drawn with its moment centroid and minimum-enclosing circle.

### Per-frame processing time (green-object tracker, PiCam2 @ 1280×720)

![performance](results/contour_detection/performance/Figure_1.png)

Logged with `src/vision/contour_detection/performance_logging.py` over 150 frames.

### Arrow direction detection

![arrow detection](results/arrow_detection/performance/plot1.png)

Single-image and live-video classifiers (`LEFT` / `RIGHT` / `UP` / `DOWN`) using contour PCA to find the principal axis and the narrower-tail end as the tip.

---

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi 4 | Main compute, Python runtime, vision |
| PiCamera 2 | 1280×720 video input |
| Arduino Nano (ATmega328P) | IMU host, serial bridge to Pi over USB |
| BNO055 | 9-DOF absolute orientation sensor (I²C to Nano) |
| L298N | Dual H-bridge motor driver |
| Skid-steer drivetrain | 65 mm wheels, 10 counts/rev × 120:1 geared encoders, 0.14 m wheelbase |
| HC-SR04 | Ultrasonic distance sensor (TRIG=23, ECHO=24) |
| Proton servo (180°) | Gripper actuation |

GPIO map (BCM): motor IN1=6, IN2=13, IN3=19, IN4=26; encoders left=4, right=18; ultrasonic TRIG=23, ECHO=24; gripper servo=16. IMU arrives over `/dev/ttyUSB0` at 9600 baud.

See [`src/arduino_nano/README.md`](src/arduino_nano/README.md) for the IMU streaming firmware and wiring.

---

## Repo layout

```
.
├── assets/images/                    # test images (traffic light, arrows, colored objects)
├── data/                             # logged runtime data (CSV / TXT)
│   ├── arrow_detection/
│   ├── contour_detection/
│   └── encoder_imu_fusion/
├── datasheets/                       # hardware reference PDFs and pinout diagrams
├── demos/                            # demo videos of working subsystems
├── grand_challenge/                  # ENPM 701 Grand Challenge integration code
├── results/                          # generated plots, annotated images, videos
│   ├── arrow_detection/
│   ├── contour_detection/
│   └── encoder_imu_fusion/
├── src/
│   ├── arduino_nano/                 # BNO055 → serial firmware (C++)
│   ├── localization/encoder_imu_fusion/
│   │   ├── encoder.py                # encoder-only rectangle run
│   │   ├── imuencoder.py             # fused encoder + IMU rectangle run
│   │   └── plotter.py                # CSV → trajectory + heading plots
│   ├── utils/                        # hardware sanity-check scripts
│   └── vision/
│       ├── arrow_detection/
│       ├── color_picker/
│       └── contour_detection/
├── Arena_layout_and_QR_Codes.pdf     # physical arena map for nav tasks
├── setup.sh                          # one-shot Raspberry Pi setup
├── requirements.txt                  # pip deps (works on laptop too)
├── LICENSE
└── README.md
```

---

## Quickstart

### On a Raspberry Pi (Bookworm 64-bit)

```bash
git clone https://github.com/ravivkrahul/Autonomous-Robot-Build-Series
cd Autonomous-Robot-Build-Series
chmod +x setup.sh
./setup.sh
source venv/bin/activate
```

`setup.sh` installs apt packages (`python3-picamera2`, `libzbar0`, `i2c-tools`, OpenCV build deps, `rpicam-apps`), creates a venv with `--system-site-packages` (so picamera2 is visible), installs pip deps, and enables I²C / SSH / VNC via `raspi-config`.

### On a laptop (just to view results / re-run plots)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The image-based and CSV-plotting scripts will run anywhere. The PiCam / GPIO scripts won't — they're hardware-bound.

---

## Run a module

Every script resolves its paths relative to the repo root, so you can run them from anywhere.

**Contour detection on the traffic-light image**
```bash
python src/vision/contour_detection/contour_detection.py
```

**Side-by-side HSV pipeline visualization**
```bash
python src/vision/contour_detection/hsv_masking.py
```

**Live green-object tracker (Pi only — needs PiCam2)** — press `r` to start a 60-s recording, `q` to quit
```bash
python src/vision/contour_detection/object_tracking.py
```

**Arrow direction classifier**
```bash
python src/vision/arrow_detection/arrow_detection_image.py        # one image
python src/vision/arrow_detection/arrow_detection_video.py        # live PiCam stream
```

**Rectangle localization run (Pi only — drives motors)**
```bash
python src/localization/encoder_imu_fusion/encoder.py             # encoder only
python src/localization/encoder_imu_fusion/imuencoder.py          # fused
```

**Plot a logged run**
```bash
python src/localization/encoder_imu_fusion/plotter.py --mode encoder
python src/localization/encoder_imu_fusion/plotter.py --mode encoder_imu
```

**Flash the IMU firmware** — open `src/arduino_nano/imudatastreaming_arduino.cpp` in the Arduino IDE, board: `Arduino Nano (ATmega328P, Old Bootloader)`, port: `/dev/ttyUSB0`. Required libraries: `Adafruit BNO055`, `Adafruit Unified Sensor`.

---

## Per-module documentation

- [`src/vision/`](src/vision/README.md) — HSV ranges, contour pipeline, arrow PCA, color picker tools
- [`src/localization/encoder_imu_fusion/`](src/localization/encoder_imu_fusion/README.md) — robot constants, PID gains, why the IMU fusion helps
- [`src/utils/`](src/utils/README.md) — hardware sanity-check scripts (one paragraph per script)
- [`src/arduino_nano/`](src/arduino_nano/README.md) — IMU firmware, wiring, serial format

---

## License

MIT — see [LICENSE](LICENSE).

## Author

**Rahul Ravi VK** — M.Eng. Robotics, University of Maryland.  Robotics · Controls · Perception.
