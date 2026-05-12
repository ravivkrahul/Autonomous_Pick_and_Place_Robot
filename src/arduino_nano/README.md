# Arduino Nano + BNO055 IMU firmware

Streams BNO055 orientation data over USB serial so the Raspberry Pi can read it as a plain text stream.

```
BNO055 ──(I²C)──► Arduino Nano ──(USB serial @ 9600)──► Raspberry Pi
                                                            │
                                                            ▼
                                                   src/utils/imudatareader.py
                                                   src/localization/...
```

## Hardware

- Arduino Nano (ATmega328P) — most clones are CH340-based and need the **Old Bootloader** option in the IDE.
- BNO055 9-DOF absolute orientation sensor.
- Breadboard, jumpers, USB data cable (not charge-only).

## Wiring

| Arduino Nano | BNO055 |
|---|---|
| 5V  | VIN |
| GND | GND |
| A5  | SCL |
| A4  | SDA |

## Flashing the firmware (Ubuntu / Raspberry Pi OS)

```bash
cd ~/Downloads
wget https://downloads.arduino.cc/arduino-ide/arduino-ide_latest_Linux_64bit.AppImage
chmod +x arduino-ide_latest_Linux_64bit.AppImage
./arduino-ide_latest_Linux_64bit.AppImage
```

In the IDE:

1. **Board**: `Arduino Nano`
2. **Processor**: `ATmega328P` (try `ATmega328P (Old Bootloader)` if upload fails — most clones need this)
3. **Port**: `/dev/ttyUSB0`
4. **Sketch → Include Library → Manage Libraries...** — install `Adafruit BNO055` and `Adafruit Unified Sensor`
5. Open `imudatastreaming_arduino.cpp` and upload

Expected serial output:

```
359.93,4.50,5.43
heading,pitch,roll
```

## Pi-side test

```bash
pip install pyserial
python src/utils/imudatareader.py
```

If you hit a permission error on `/dev/ttyUSB0`, add yourself to the dialout group:

```bash
sudo usermod -aG dialout $USER
# log out and back in
```

If the device doesn't appear at all, the most common cause on a CH340 clone is `brltty` grabbing the port. Remove it:

```bash
sudo apt remove brltty
```

> **Power note:** the Nano should be powered from the Pi's USB port (not externally), so the same cable carries the serial stream.

## Author

Rahul Ravi VK — Robotics · Controls · Perception
