# Utility scripts

Hardware sanity-check / bring-up scripts. Each is standalone — run it directly when you want to verify one specific subsystem before pulling it into a larger program.

| Script | Use it when |
|---|---|
| `picam2_image_capture_test.py` | First-time camera check — capture a single still and confirm PiCam2 + libcamera are wired up. |
| `picam2_video_capture_test.py` | Confirm video pipeline (H.264 encoder, FFmpeg output) works end-to-end. |
| `live_hsv_tuner.py` | Tune HSV ranges against the **live** PiCam2 feed via trackbars. Like `color_picker/colorpicker.py` but with motion / lighting variation. |
| `roitester.py` | Test region-of-interest cropping on the live stream — useful before adding ROI gating to a detector. |
| `center_tuning_script.py` | Tune object-centering behavior (per-color HSV mask + pixel-error-from-center readout) before running a full color-following mission. |
| `distance_calibration_all_colors.py` | Sweep distances against a colored target and fit a pixel-area → distance curve for each color. Writes the fitted parameters to disk. |
| `qrcode_reader.py` | Live QR-code decoder using `pyzbar`. Pair with the arena layout in `Arena_layout_and_QR_Codes.pdf`. |
| `imudatareader.py` | Read the IMU stream from the Nano on `/dev/ttyUSB0` and print parsed `heading,pitch,roll`. First thing to run after flashing the firmware. |
| `imu_x.py` | Smaller version of the above — prints only the heading (yaw `x`) channel. Useful as a one-liner during debugging. |
| `encoderdebug.py` | Polling-based encoder counter with WASD teleop. Drives the motors and prints left/right counts so you can verify wiring and counts/rev. |
| `gripper_test_tune.py` | Sweep the gripper servo close → open → close. Use to find your specific servo's `GRIP_MIN` / `GRIP_MAX` duty cycles. |
| `ultrasonic_test.py` | Continuously print HC-SR04 distance readings (TRIG=23, ECHO=24). |
| `cleanup.py` | Reset all GPIO pins to a safe input state. Run after any program that crashed and left pins driven. |

## Conventions

- All Pi-only scripts assume BCM pin numbering.
- Serial scripts target `/dev/ttyUSB0` at 9600 baud (matches `src/arduino_nano/imudatastreaming_arduino.cpp`).
- Press `Ctrl+C` to exit; the IMU/encoder scripts call `GPIO.cleanup()` in their `finally` blocks, but if one crashes hard, run `cleanup.py` afterward.
