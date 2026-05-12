#!/usr/bin/env bash
# ============================================================
# Autonomous Robot Build Series — one-shot setup script
# Target: Raspberry Pi OS Bookworm (64-bit) on Raspberry Pi 4/5
# Usage:  chmod +x setup.sh && ./setup.sh
#
# This script is the modernized 2026 equivalent of the ENPM 701
# Lecture 02 setup deck (Raspbian Buster, picamera legacy, etc.)
# updated for: Bookworm, PEP 668 venvs, picamera2, rpicam-apps.
# ============================================================

set -e  # exit immediately if any command fails

echo "=========================================="
echo " Autonomous Robot — Environment Setup"
echo "=========================================="

# ------------------------------------------------------------
# 0. Sanity: confirm we're on a Raspberry Pi
# ------------------------------------------------------------
if ! grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Not running on a Raspberry Pi — some steps (GPIO, I2C, camera) will fail."
    echo "    Continuing anyway; comment out the Pi-only lines if you hit errors."
    sleep 2
fi

# Print OS info (equivalent to slide 15: cat /etc/os-release)
echo ""
echo "Detected OS:"
grep -E '^(PRETTY_NAME|VERSION_CODENAME)=' /etc/os-release || true

# ------------------------------------------------------------
# 1. System packages (apt)
# ------------------------------------------------------------
echo ""
echo "[1/5] Installing core system packages via apt..."
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-picamera2 \
    libzbar0 \
    libatlas-base-dev \
    i2c-tools \
    git \
    rpicam-apps

# ------------------------------------------------------------
# 2. OpenCV build-dependency fallback
#    Modern pip wheels usually avoid needing these, but keep as
#    a fallback in case opencv-python has to compile from source.
#    (Slide 22 of ENPM 701 deck — updated for Bookworm package names.)
# ------------------------------------------------------------
echo ""
echo "[2/5] Installing OpenCV build-dependency fallback..."
sudo apt install -y \
    libhdf5-dev \
    libhdf5-serial-dev \
    libjpeg-dev \
    libtiff-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    python3-pyqt5 || echo "  (some optional packages failed — usually fine)"

# ------------------------------------------------------------
# 3. Python virtual environment
#    --system-site-packages lets the venv see picamera2 (apt)
# ------------------------------------------------------------
echo ""
echo "[3/5] Creating Python virtual environment (venv/)..."
python3 -m venv venv --system-site-packages
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip

# ------------------------------------------------------------
# 4. Python packages (pip)
# ------------------------------------------------------------
echo ""
echo "[4/5] Installing Python packages via pip..."

pip install \
    "numpy<2.0" \
    opencv-python \
    matplotlib \
    pandas \
    scipy \
    pyserial \
    pyzbar \
    Pillow \
    tqdm \
    imutils \
    gpiozero \
    RPi.GPIO \
    adafruit-circuitpython-bno055 \
    adafruit-blinka

# ------------------------------------------------------------
# 5. Enable interfaces: I2C, Camera, SSH, VNC
#    (Slides 10, 26-28 of the deck — consolidated via raspi-config)
# ------------------------------------------------------------
echo ""
echo "[5/5] Enabling I2C, Camera, SSH, VNC..."
if command -v raspi-config &>/dev/null; then
    sudo raspi-config nonint do_i2c 0        # Enable I2C
    sudo raspi-config nonint do_ssh 0        # Enable SSH
    sudo raspi-config nonint do_vnc 0 || \
        echo "  (VNC: realvnc-vnc-server not installed — run 'sudo apt install realvnc-vnc-server' if needed)"
    # Camera is auto-enabled on Bookworm via libcamera; no raspi-config step needed.
else
    echo "  raspi-config not found — skipping interface enable."
fi

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------
echo ""
echo "=========================================="
echo " Setup complete."
echo "=========================================="
echo ""
echo " To start working:"
echo "     source venv/bin/activate"
echo ""
echo " To find your Pi's IP (for SSH / VNC):"
echo "     hostname -I"
echo ""
echo " To test the camera (modern Bookworm commands):"
echo "     rpicam-still -o testpic.jpg           # still image"
echo "     rpicam-vid -o testvid.mp4 -t 5000     # 5-second video"
echo "     python src/utils/picam2_image_capture_test.py"
echo ""
echo " To test the IMU (serial from Arduino):"
echo "     python src/utils/imudatareader.py"
echo ""
echo " If you enabled VNC, connect from your laptop with:"
echo "     VNC Viewer -> <Pi-IP-address>"
echo ""
