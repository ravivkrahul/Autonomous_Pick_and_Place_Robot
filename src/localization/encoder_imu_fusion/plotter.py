"""
Plot a logged rectangle trajectory from a CSV produced by encoder.py
or imuencoder.py.

Usage:
    python plotter.py                          # plots encoder-only
    python plotter.py --mode encoder_imu       # plots fused encoder + IMU
    python plotter.py --mode encoder           # explicit encoder-only

The CSV is read from data/encoder_imu_fusion/.
"""

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -----------------------------
# CLI
# -----------------------------
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument(
    "--mode",
    choices=["encoder", "encoder_imu"],
    default="encoder",
    help="Which run to plot (default: encoder)",
)
args = parser.parse_args()

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "encoder_imu_fusion"
csv_map = {
    "encoder": DATA_DIR / "encoder_only_rectangle.csv",
    "encoder_imu": DATA_DIR / "encoder_imu_rectangle.csv",
}
file_path = csv_map[args.mode]

if not file_path.exists():
    raise FileNotFoundError(f"No CSV at {file_path}. Run encoder.py / imuencoder.py first.")

df = pd.read_csv(file_path)

for col in ["time", "imu_x", "x", "y"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["time", "imu_x", "x", "y"])

# -----------------------------
# Original (x, y) trajectory
# -----------------------------
x = df["x"].values
y = df["y"].values

# Rotate so that the first heading aligns with 0 deg
theta0 = np.radians(df["imu_x"].iloc[0])
x_rot = x * np.cos(theta0) + y * np.sin(theta0)
y_rot = -x * np.sin(theta0) + y * np.cos(theta0)

# Flip vertically (most natural display orientation)
y_rot = -y_rot

# -----------------------------
# Path plot
# -----------------------------
plt.figure(figsize=(7, 7))
plt.plot(x_rot, y_rot, marker="o", linewidth=2)
plt.xlabel("X (m)")
plt.ylabel("Y (m)")
plt.title(f"Robot path  [{args.mode}]")
plt.grid(True)
plt.axis("equal")

# -----------------------------
# Heading vs time
# -----------------------------
plt.figure(figsize=(10, 5))
plt.plot(df["time"], df["imu_x"], linewidth=2)
plt.xlabel("Time (s)")
plt.ylabel("IMU heading (deg)")
plt.title(f"IMU heading vs time  [{args.mode}]")
plt.grid(True)

plt.show()
