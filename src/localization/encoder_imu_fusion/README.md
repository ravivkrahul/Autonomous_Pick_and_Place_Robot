# Encoder vs. Encoder + IMU localization

The experiment: drive the same commanded 1.4 m × 1.0 m rectangle twice — once using wheel encoders for both **distance** and **heading**, once using wheel encoders for **distance only** and the BNO055 IMU yaw for **heading** — and compare the resulting (x, y) trajectories logged to CSV.

## Files

| File | Role |
|---|---|
| `encoder.py` | Encoder-only run. Straight-line PWM ratio holds straight; 90° pivots use encoder count targets derived from the geometry. Logs to `data/encoder_imu_fusion/encoder_only_rectangle.csv`. |
| `imuencoder.py` | Fused run. Encoders for distance, IMU yaw PID holds heading during straight segments, 90° turns close on the live IMU heading. Logs to `data/encoder_imu_fusion/encoder_imu_rectangle.csv`. |
| `plotter.py` | Reads either CSV (`--mode encoder` or `--mode encoder_imu`) and produces the trajectory plot + heading-vs-time plot. |

## Robot constants (both scripts use the same values)

| Quantity | Value |
|---|---|
| Wheel diameter | 0.065 m |
| Wheel circumference | π × 0.065 = 0.2042 m |
| Counts per rev (post-gearbox) | 10 |
| **Meters per encoder count** | **0.02042 m** |
| Wheelbase | 0.152 m (`encoder.py`) |
| Track length | 0.14 m |
| Effective pivot radius | √((wheelbase/2)² + (track/2)²) |
| Slip factor (pivots) | 1.265 |
| Rectangle long side | 1.4 m |
| Rectangle short side | 1.0 m |
| Control timestep `DT` | 0.02 s (50 Hz) |

> Note on encoder resolution: 10 counts/rev is the **post-gearbox** count seen at the wheel. The motor itself has a 120:1 reduction.

## Control gains

**Straight motion (heading PID, fused script)** — keeps the robot pointed at the heading captured at the start of each straight leg.

| Gain | Value |
|---|---|
| `KP_HEAD` | 1.0 |
| `KI_HEAD` | 0.02 |
| `KD_HEAD` | 0.10 |
| `I_CLAMP_HEAD` | ±15.0 |
| `BASE_PWM_LEFT` | 58 |
| `BASE_PWM_RIGHT` | 62 (motors aren't symmetric) |
| `PWM_MIN_FWD` / `PWM_MAX_FWD` | 35 / 100 |

**Pivot turns (fused script)** — close on a 90° change from the live IMU heading.

| Gain | Value |
|---|---|
| `KP_TURN` | 0.55 |
| `KI_TURN` | 0.03 |
| `I_CLAMP_TURN` | ±20.0 |
| `TURN_PWM_MIN` / `MAX` | 60 / 76 (high enough to overcome static friction) |
| `TURN_TOL` | 1.1° |

## What the IMU fusion fixes

Each pivot turn in the encoder-only run accumulates a small heading error (slip on the floor, slight wheel-radius mismatch, integer count rounding). After four 90° pivots, that error compounds into a noticeably non-closed rectangle. The IMU yaw, despite its own drift, is observed **per turn** by a PID closing on the absolute heading, so the per-turn error stays bounded instead of accumulating.

You can see the difference in `results/encoder_imu_fusion/encoder_only.png` vs `results/encoder_imu_fusion/imu_encoder.png`.

## Sign convention quirk to watch for

Left turn → IMU `imu_x` heading **decreases**. So in the straight-line heading PID:

```
heading_error = wrap_to_180(heading_ref - current_heading)
```

A positive error means the robot drifted left (current < ref), and the correct response is to steer right, which means:

```
left_pwm  = BASE + correction      ◄── speeds up the left wheel
right_pwm = BASE − correction      ◄── slows down the right wheel
```

If you flip the sign and the robot loops left into a wall on the first segment, that's why.

## Hardware prerequisites

- BNO055 IMU streaming `heading,pitch,roll` over USB serial (`/dev/ttyUSB0`, 9600 baud) — see [`src/arduino_nano/README.md`](../../arduino_nano/README.md).
- L298N motor driver wired to BCM pins 6/13/19/26.
- Quadrature encoders on BCM 4 (left) and BCM 18 (right). The code only counts rising edges (no quadrature decode), so it can't detect direction — fine for forward-only programs.

## CSV log format

Both scripts log the same columns:

| Column | Meaning |
|---|---|
| `time`   | seconds since start |
| `imu_x`  | IMU yaw (degrees) |
| `x`, `y` | dead-reckoned position (meters) |
| `phase`  | label of the current motion phase (`forward_1`, `turn_2`, etc.) |

`plotter.py` rotates the trajectory so the first sample's heading aligns with the +X axis, then flips Y to display in screen-natural orientation.
