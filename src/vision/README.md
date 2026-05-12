# Vision

Three independent vision modules. All paths inside the scripts resolve relative to the repo root, so any of them can be run from any working directory.

## `contour_detection/`

A small HSV-based color segmentation + contour analysis pipeline, evolving from a single-image demo to a logged live-camera tracker.

| Script | What it does |
|---|---|
| `contour_detection.py` | One-shot: load `traffic_light.jpg`, run the full HSV → contour → centroid → enclosing-circle pipeline, show the green-light overlay. |
| `hsv_masking.py` | Diagnostic stack: \[original \| HSV \| red mask \| red applied \| yellow mask \| yellow applied \| green mask \| green applied\] in one window. Useful for eyeballing HSV ranges. |
| `object_tracking.py` | Live PiCam2 green-object tracker @ 1280×720. Press `r` to record a 60-s clip into `results/contour_detection/videos/`; `q` to quit. |
| `performance_logging.py` | Same tracker, but also appends per-frame processing time (in seconds) to `data/contour_detection/recording_data.txt`. |
| `performance_plotting.py` | Reads that log and produces a 2-panel figure: frame-vs-time and a histogram. |
| `video_creator_from_frames.py` | Renders the static HSV pipeline stages into a presentation-grade MP4 (H.264 + AAC) using FFmpeg. |

### HSV ranges used (8-bit, OpenCV order H ∈ \[0,179\], S/V ∈ \[0,255\])

| Color | Lower (H,S,V) | Upper (H,S,V) |
|---|---|---|
| Red   | (167, 170, 40) | (179, 255, 255) |
| Yellow| (20, 157, 40)  | (40, 255, 255)  |
| Green | (45, 80, 70)   | (95, 255, 255)  |

Tune your own with `src/vision/color_picker/colorpicker.py` (image-based) or `src/utils/live_hsv_tuner.py` (live camera).

### Pipeline (one frame)

```
BGR frame ─► cvtColor BGR→HSV ─► inRange(lower, upper) ─► findContours
                                                              │
                                                              ▼
                                                  max(contourArea)
                                                              │
                                          ┌──────────────────┴───────────────────┐
                                          ▼                                       ▼
                                 minEnclosingCircle(c)                    moments(c) → centroid
```

Both the moment centroid and the min-enclosing-circle center are drawn — they disagree slightly on asymmetric blobs, and that disagreement is the point of showing both.

## `arrow_detection/`

A direction classifier (`LEFT` / `RIGHT` / `UP` / `DOWN`) for an arrow-shaped blob, using contour PCA to find the principal axis, then deciding which end is the **tip** vs the **tail** by measuring the perpendicular width at each extreme — the tip is the narrower end.

```
HSV mask (green)
   │
   ▼
findContours → largest contour
   │
   ▼
points = squeeze(contour)
centered = points - mean(points)
cov = centeredᵀ · centered / (n-1)
eigvals, eigvecs = eig(cov)
axis = eigvec with max eigval          ◄── principal axis
perp = (−axis_y, axis_x)               ◄── perpendicular axis
proj = centered · axis                 ◄── 1-D projection onto principal axis
   │
   ▼
min_region = points where proj ≈ min_proj    (one end of the arrow)
max_region = points where proj ≈ max_proj    (other end)
min_width = spread of min_region along perp
max_width = spread of max_region along perp
tip = whichever end is NARROWER (tip is pointier than tail)
   │
   ▼
direction from arctan2(−dy, dx) between tip and centroid, quantized into 4 bins
```

| Script | What it does |
|---|---|
| `arrow_detection_image.py` | Run on `assets/images/arrow.JPG`, print + draw the detected direction. |
| `arrow_detection_video.py` | Live PiCam2 version. Press `r` to start recording (saves into `results/arrow_detection/videos/` + appends frame times to `data/arrow_detection/hw4_recording_data.txt`), `s` to stop, `q` to quit. |

## `color_picker/`

| Script | What it does |
|---|---|
| `colorpicker.py` | Trackbar-based HSV / RGB range picker on a static image. `python colorpicker.py -i path/to/img.jpg -f HSV` (`-f` is `RGB` or `HSV`). Useful for finding lower/upper ranges before plugging them into the detection scripts. |
