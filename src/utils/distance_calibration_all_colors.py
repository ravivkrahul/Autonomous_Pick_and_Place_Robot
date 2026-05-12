#!/usr/bin/env python3

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import csv
import os
import select
import sys

# ==========================================================
# CAMERA / CALIBRATION SETTINGS
# ==========================================================
WIDTH = 640
HEIGHT = 480
MIN_CONTOUR_AREA = 500

# Distances measured from CAMERA LENS to front face of block
# DISTANCES_INCH = [12, 24, 36, 48, 60, 72, 84, 96, 108, 120]
DISTANCES_INCH = [12, 18, 24, 30, 36, 42, 48, 60, 72, 84]
COLORS = ["red", "green", "blue"]

OUTPUT_CSV = "distance_calibration_all_colors.csv"
OUTPUT_PARAMS = "distance_params_all_colors.txt"

# Capture settings
RECORD_SECONDS = 2.0
FRAME_DELAY = 0.03
FLUSH_COUNT = 4
SETTLE_S = 0.15

# ==========================================================
# HSV MASKS
# Use the same tuned thresholds as your latest main robot code.
# Do not change these unless your live detection is wrong.
# ==========================================================
def get_mask(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    if color == "red":
        
        mask1 = cv2.inRange(hsv, np.array([0, 168, 37]), np.array([20, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([161, 175, 120]), np.array([180, 255, 255]))
        mask = mask1 | mask2

    elif color == "green":
        # mask = cv2.inRange(hsv, np.array([50, 170, 148]), np.array([100, 255, 255]))
        mask = cv2.inRange(hsv, np.array([50, 170, 110]), np.array([100, 255, 255]))

        
    elif color == "blue":
        mask = cv2.inRange(hsv, np.array([100, 173, 110]), np.array([124, 255, 255]))
    else:
        raise ValueError(f"Invalid color: {color}")

    k = np.ones((5, 5), np.uint8)
    mask = cv2.erode(mask, k, iterations=1)
    mask = cv2.dilate(mask, k, iterations=2)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    return mask

# ==========================================================
# FRAME / DETECTION
# ==========================================================
def get_fresh_frame(picam2, flush_count=FLUSH_COUNT, settle_s=SETTLE_S):
    time.sleep(settle_s)
    frame = None
    for _ in range(flush_count):
        frame = picam2.capture_array()
    return frame


def detect_object(frame, color):
    mask = get_mask(frame, color)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, mask

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)

    if area < MIN_CONTOUR_AREA:
        return None, mask

    M = cv2.moments(contour)
    if M["m00"] == 0:
        return None, mask

    x, y, w, h = cv2.boundingRect(contour)
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return {
        "x": x, "y": y, "w": w, "h": h,
        "area": area, "cx": cx, "cy": cy,
        "contour": contour,
    }, mask


def draw_debug(frame, mask, obj, color, message):
    debug = frame.copy()

    cv2.putText(debug, message, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    cv2.line(debug, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), (0, 255, 0), 1)
    cv2.line(debug, (0, HEIGHT // 2), (WIDTH, HEIGHT // 2), (0, 255, 0), 1)

    if obj is not None:
        x, y, w, h = obj["x"], obj["y"], obj["w"], obj["h"]
        cx, cy = obj["cx"], obj["cy"]
        cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(debug, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(debug, f"{color.upper()} h={h}px area={obj['area']:.0f}",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    else:
        cv2.putText(debug, f"NO {color.upper()} DETECTED",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

    preview = cv2.bitwise_and(frame, frame, mask=mask)
    cv2.imshow("Live Camera", debug)
    cv2.imshow("Mask", mask)
    cv2.imshow("Masked Preview", preview)
    cv2.waitKey(1)


# ==========================================================
# USER INPUT
# ==========================================================
def enter_pressed():
    try:
        if select.select([sys.stdin], [], [], 0.02)[0]:
            line = sys.stdin.readline()
            return line == "\n"
    except Exception:
        return False
    return False


def wait_for_enter_live(picam2, color, distance_in):
    print(f"\n[{color.upper()}] Place object at {distance_in} inches from CAMERA lens.")
    print("Check live feed/mask. Press ENTER in terminal when ready.")

    while True:
        frame = picam2.capture_array()
        obj, mask = detect_object(frame, color)
        draw_debug(frame, mask, obj, color, f"{color.upper()} at {distance_in} in | ENTER when ready")

        if enter_pressed():
            return


def record_sample(picam2, color, distance_in):
    samples = []
    start = time.time()

    print(f"Recording {color.upper()} at {distance_in} in... keep object still.")

    # Flush once before collecting samples
    _ = get_fresh_frame(picam2)

    while time.time() - start < RECORD_SECONDS:
        frame = picam2.capture_array()
        obj, mask = detect_object(frame, color)

        if obj is not None:
            samples.append(obj["h"])

        draw_debug(frame, mask, obj, color, f"Recording {color.upper()} {distance_in} in")
        time.sleep(FRAME_DELAY)

    return samples

# ==========================================================
# FITTING
# ==========================================================
def fit_abc(rows_for_color):
    """
    Fits: distance_cm = A/h + B/h^2 + C
    Needs at least 3 valid samples.
    """
    heights = np.array([r["bbox_height_px"] for r in rows_for_color], dtype=float)
    dists = np.array([r["distance_cm"] for r in rows_for_color], dtype=float)

    X = np.column_stack([
        1.0 / heights,
        1.0 / (heights ** 2),
        np.ones_like(heights),
    ])

    A, B, C = np.linalg.lstsq(X, dists, rcond=None)[0]
    pred = (A / heights) + (B / (heights ** 2)) + C
    err = pred - dists
    mae = float(np.mean(np.abs(err)))
    max_abs = float(np.max(np.abs(err)))

    return A, B, C, pred, err, mae, max_abs


def print_fit_report(color, rows):
    if len(rows) < 3:
        print(f"\n{color.upper()}: Not enough valid points to fit. Need at least 3.")
        return None

    A, B, C, pred, err, mae, max_abs = fit_abc(rows)

    print(f"\n================ {color.upper()} FIT ================")
    print("Use these in robot code:")
    print(f"DIST_A_{color.upper()} = {A:.6f}")
    print(f"DIST_B_{color.upper()} = {B:.6f}")
    print(f"DIST_C_{color.upper()} = {C:.6f}")
    print(f"MAE={mae:.2f} cm | MAX_ERR={max_abs:.2f} cm")
    print("-----------------------------------------------------")
    for row, p, e in zip(rows, pred, err):
        print(f"actual={row['distance_cm']:7.2f} cm | h={row['bbox_height_px']:7.2f}px | "
              f"pred={p:7.2f} cm | err={e:+6.2f} cm")

    return {
        "color": color,
        "A": A,
        "B": B,
        "C": C,
        "mae": mae,
        "max_abs": max_abs,
    }


# ==========================================================
# MAIN
# ==========================================================
def main():
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (WIDTH, HEIGHT)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    time.sleep(2)

    all_rows = []
    fit_params = []

    print("\nDistance Calibration Started for RED, GREEN, BLUE")
    print("Distance is measured from CAMERA LENS to block front face.")
    print("Live Camera, Mask, and Masked Preview windows will open.")
    print("Press ENTER after placing each block at the requested distance.\n")

    try:
        for color in COLORS:
            print(f"\n====================================================")
            print(f"STARTING {color.upper()} CALIBRATION")
            print(f"====================================================")

            color_rows = []

            for d_in in DISTANCES_INCH:
                wait_for_enter_live(picam2, color, d_in)
                samples = record_sample(picam2, color, d_in)

                if len(samples) == 0:
                    print(f"WARNING: No {color.upper()} object detected at {d_in} in. Skipping.")
                    continue

                avg_h = float(np.mean(samples))
                std_h = float(np.std(samples))
                d_cm = float(d_in * 2.54)

                row = {
                    "color": color,
                    "distance_in": float(d_in),
                    "distance_cm": d_cm,
                    "bbox_height_px": avg_h,
                    "std_height_px": std_h,
                    "samples": len(samples),
                }
                all_rows.append(row)
                color_rows.append(row)

                print(f"Saved {color.upper()} {d_in} in | {d_cm:.2f} cm | "
                      f"h={avg_h:.2f}px std={std_h:.2f}px samples={len(samples)}")

            params = print_fit_report(color, color_rows)
            if params is not None:
                fit_params.append(params)

        # Save CSV
        with open(OUTPUT_CSV, "w", newline="") as f:
            fieldnames = ["color", "distance_in", "distance_cm",
                          "bbox_height_px", "std_height_px", "samples"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        # Save parameter text file
        with open(OUTPUT_PARAMS, "w") as f:
            f.write("# Distance model: distance_cm = A/h + B/(h*h) + C\n\n")
            for p in fit_params:
                c = p["color"]
                f.write(f"DIST_PARAMS['{c}'] = ({p['A']:.6f}, {p['B']:.6f}, {p['C']:.6f})\n")
            f.write("\n# Helper for robot code:\n")
            f.write("""
DIST_PARAMS = {
    'red':   (0.0, 0.0, 0.0),
    'green': (0.0, 0.0, 0.0),
    'blue':  (0.0, 0.0, 0.0),
}

def estimate_distance_cm(h, color):
    if h <= 0:
        return 999.0
    A, B, C = DIST_PARAMS[color]
    return (A / h) + (B / (h * h)) + C
""")

        print(f"\nSaved calibration CSV: {os.path.abspath(OUTPUT_CSV)}")
        print(f"Saved parameter file : {os.path.abspath(OUTPUT_PARAMS)}")

        print("\nCopy this style into the robot code:")
        print("DIST_PARAMS = {")
        for p in fit_params:
            print(f"    '{p['color']}': ({p['A']:.6f}, {p['B']:.6f}, {p['C']:.6f}),")
        print("}")
        print("""
def estimate_distance_cm(h, color):
    if h <= 0:
        return 999.0
    A, B, C = DIST_PARAMS[color]
    return (A / h) + (B / (h * h)) + C
""")

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
