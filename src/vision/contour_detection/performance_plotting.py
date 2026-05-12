"""
Plot per-frame processing time for the green-object tracker.

Reads `data/contour_detection/recording_data.txt` (one float per line, in
seconds), converts to ms, and produces a 2-row figure:
    1. Frame index vs processing time
    2. Histogram of processing times

Run from anywhere:
    python src/vision/contour_detection/performance_plotting.py
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "contour_detection" / "recording_data.txt"

# Load data (seconds per frame) -> ms
data = np.loadtxt(DATA_PATH)
data_ms = data * 1000.0
frames = np.arange(len(data_ms))

# -----------------------------
# Plot 1: Frame vs Processing Time
# -----------------------------
plt.figure(1, figsize=(9, 7))
plt.subplot(2, 1, 1)
plt.plot(frames, data_ms, "b-o", markersize=4, linewidth=1, label="Raw data")
plt.title(f"Object tracking: per-frame processing time  (mean={data_ms.mean():.2f} ms)")
plt.xlabel("Frame")
plt.ylabel("Processing time [ms]")
plt.xlim(0, max(0, len(data_ms) - 1))
plt.grid(True)
plt.legend()

# -----------------------------
# Plot 2: Histogram
# -----------------------------
plt.subplot(2, 1, 2)
plt.hist(data_ms, bins=50)
plt.title("Processing-time distribution")
plt.xlabel("Processing time [ms]")
plt.ylabel("Frames")
plt.grid(True)

plt.tight_layout()
plt.show()
