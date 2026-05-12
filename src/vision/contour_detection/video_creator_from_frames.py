"""
Traffic Light HSV Detection — Video Generator
Outputs an H.264 + AAC MP4 compatible with Google Vids / Drive / Slides.

Requirements:
  pip install opencv-python numpy
  FFmpeg must be installed and on your PATH.
    - Windows: https://www.gyan.dev/ffmpeg/builds/  (add bin/ to PATH)
    - Mac:     brew install ffmpeg
    - Linux:   sudo apt install ffmpeg
"""

import cv2 as cv
import numpy as np
import subprocess
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# ── Config ──────────────────────────────────────────────────────────────
INPUT_IMAGE = str(REPO_ROOT / "assets" / "images" / "traffic_light.jpg")
OUTPUT_DIR = REPO_ROOT / "results" / "contour_detection" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_VIDEO = str(OUTPUT_DIR / "traffic_light_detection.mp4")
FPS = 30
DISPLAY_WIDTH = 640            # Frames resized to this width
HOLD_SECONDS = 2               # How long each stage stays on screen
FADE_SECONDS = 0.5             # Crossfade duration between stages

# ── Preflight: check FFmpeg ─────────────────────────────────────────────
if not shutil.which("ffmpeg"):
    print("ERROR: FFmpeg not found on PATH.")
    print("Install it first — see instructions at top of this script.")
    sys.exit(1)

# ── Load image ──────────────────────────────────────────────────────────
image = cv.imread(INPUT_IMAGE)
if image is None:
    print(f"ERROR: Could not load '{INPUT_IMAGE}'. Check the file path.")
    sys.exit(1)

# ── Processing (same as your original code) ─────────────────────────────
hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)

red_lower   = np.array([160, 80, 40])
red_upper   = np.array([179, 255, 255])
yellow_lower = np.array([20, 157, 40])
yellow_upper = np.array([40, 255, 255])
green_lower = np.array([45, 80, 70])
green_upper = np.array([95, 255, 255])

mask_red    = cv.inRange(hsv_image, red_lower, red_upper)
mask_yellow = cv.inRange(hsv_image, yellow_lower, yellow_upper)
mask_green  = cv.inRange(hsv_image, green_lower, green_upper)

red_image    = cv.bitwise_and(image, image, mask=mask_red)
yellow_image = cv.bitwise_and(image, image, mask=mask_yellow)
green_image  = cv.bitwise_and(image, image, mask=mask_green)

mask_red_3    = cv.cvtColor(mask_red, cv.COLOR_GRAY2BGR)
mask_yellow_3 = cv.cvtColor(mask_yellow, cv.COLOR_GRAY2BGR)
mask_green_3  = cv.cvtColor(mask_green, cv.COLOR_GRAY2BGR)

# ── Stages ──────────────────────────────────────────────────────────────
stages = [
    ("Original Image",   image),
    ("Red Mask",          mask_red_3),
    ("Red Detected",      red_image),
    ("Original Image",   image),
    ("Yellow Mask",       mask_yellow_3),
    ("Yellow Detected",   yellow_image),
    ("Original Image",   image),
    ("Green Mask",        mask_green_3),
    ("Green Detected",    green_image),
]

# ── Helpers ─────────────────────────────────────────────────────────────

def resize_even(img, width):
    """Resize keeping aspect ratio, ensuring even dimensions for H.264."""
    h, w = img.shape[:2]
    scale = width / w
    new_w = width if width % 2 == 0 else width + 1
    new_h = int(h * scale)
    new_h = new_h if new_h % 2 == 0 else new_h + 1
    return cv.resize(img, (new_w, new_h), interpolation=cv.INTER_AREA)


def add_label(img, label, progress=None):
    out = img.copy()
    h, w = out.shape[:2]
    # Semi-transparent top banner
    banner_h = 50
    overlay = out.copy()
    cv.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 0), -1)
    cv.addWeighted(overlay, 0.6, out, 0.4, 0, out)
    cv.putText(out, label, (15, 35),
               cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv.LINE_AA)
    # Progress bar
    if progress is not None:
        bar_h = 4
        cv.rectangle(out, (0, h - bar_h), (int(w * progress), h), (0, 200, 255), -1)
    return out


def pad_to(img, target_h, target_w):
    h, w = img.shape[:2]
    if h < target_h:
        img = np.vstack([img, np.zeros((target_h - h, w, 3), dtype=np.uint8)])
    return img


# ── Prepare frames ─────────────────────────────────────────────────────
resized = [(lbl, resize_even(img, DISPLAY_WIDTH)) for lbl, img in stages]
target_h = max(s[1].shape[0] for s in resized)
target_h = target_h if target_h % 2 == 0 else target_h + 1
prepped = [(lbl, pad_to(img, target_h, DISPLAY_WIDTH)) for lbl, img in resized]

hold_frames = int(FPS * HOLD_SECONDS)
fade_frames = int(FPS * FADE_SECONDS)
n = len(prepped)
total_frames = n * hold_frames + (n - 1) * fade_frames

# ── Pipe raw frames into FFmpeg ─────────────────────────────────────────
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{DISPLAY_WIDTH}x{target_h}",
    "-r", str(FPS),
    "-i", "-",                       # read from stdin
    "-c:v", "libx264",              # H.264 codec
    "-preset", "medium",
    "-crf", "20",                    # good quality
    "-pix_fmt", "yuv420p",          # universal compatibility
    "-movflags", "+faststart",      # web/Google friendly
    "-an",                           # no audio track
    OUTPUT_VIDEO,
]

print(f"Generating {total_frames} frames at {FPS} fps...")
proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

frame_count = 0
for i, (label, img) in enumerate(prepped):
    # Hold
    for _ in range(hold_frames):
        progress = frame_count / total_frames
        proc.stdin.write(add_label(img, label, progress).tobytes())
        frame_count += 1

    # Crossfade
    if i < n - 1:
        next_label, next_img = prepped[i + 1]
        for t in range(fade_frames):
            alpha = t / fade_frames
            blended = cv.addWeighted(img, 1.0 - alpha, next_img, alpha, 0)
            cur_label = label if alpha < 0.5 else next_label
            progress = frame_count / total_frames
            proc.stdin.write(add_label(blended, cur_label, progress).tobytes())
            frame_count += 1

proc.stdin.close()
stderr = proc.stderr.read().decode()
proc.wait()

if proc.returncode != 0:
    print("FFmpeg error:\n", stderr[-500:])
    sys.exit(1)

duration = frame_count / FPS
print(f"\nDone! Video saved -> {OUTPUT_VIDEO}")
print(f"  {n} stages | {duration:.1f}s | {FPS} fps | H.264 + yuv420p")
print(f"  Ready for Google Vids / Drive / Slides")