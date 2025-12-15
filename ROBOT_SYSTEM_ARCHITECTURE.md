# ROBOT TRAINING DATA GENERATOR
## System Architecture & Engineering Plan

**Goal:** Convert demonstration videos → timestep-based robot control data
**Target:** Tesla Optimus, Figure AI, Boston Dynamics, etc.
**Format:** HDF5 (industry standard)

---

## SYSTEM REQUIREMENTS

### Input:
- Demonstration video (human performing task)
- Optional: Task description, success label

### Output:
```python
demo_001.hdf5
├── observations/
│   ├── timestamps        [T]        # Time in seconds
│   ├── images            [T,H,W,3]  # Video frames
│   ├── ee_pos            [T,3]      # End-effector xyz (meters)
│   ├── ee_quat           [T,4]      # Orientation (quaternion)
│   ├── gripper_qpos      [T,1]      # Gripper openness [0,1]
│   └── ee_velocity       [T,3]      # Velocity (m/s)
├── actions/              [T,8]      # Delta commands
│   # [delta_x, delta_y, delta_z, delta_roll, delta_pitch, delta_yaw, gripper_cmd, terminate]
└── metadata/
    ├── num_timesteps: 315
    ├── fps: 30
    ├── duration: 10.5
    ├── success: true
    └── task: "pick_and_place_cup"
```

**Key:** `T` = number of timesteps (typically 150-500 for 5-15 second demos)

---

## ARCHITECTURAL DIFFERENCES

| Aspect | Current System | Robot System |
|--------|---------------|--------------|
| **Granularity** | 4 segments | 315 timesteps |
| **Output rate** | 5 fps | 30 fps |
| **Coordinates** | Normalized [0,1] | Metric (meters) |
| **Actions** | Labels ("reach") | Commands (Δpos, Δrot) |
| **Gripper** | Static openness | Dynamic commands |
| **Format** | JSON | HDF5 |
| **Focus** | Understanding | Control |

---

## NEW PIPELINE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                  INPUT: demo.mp4 (30 fps)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         STAGE 1: FULL-RATE EXTRACTION (NO SAMPLING)          │
│  - Process ALL frames at 30fps (or native fps)              │
│  - Pose tracking: wrist position every frame                │
│  - Hand tracking: gripper state every frame                 │
│  - Object detection: every 5th frame (optimization)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           STAGE 2: COORDINATE SYSTEM CALIBRATION             │
│  - Camera intrinsics (focal length, principal point)        │
│  - Depth estimation (monocular depth or fixed distance)     │
│  - Normalized [0,1] → Metric coordinates (meters)           │
│  - World frame alignment (table plane, gravity)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              STAGE 3: TRAJECTORY SMOOTHING                   │
│  - Kalman filtering (remove jitter)                         │
│  - Velocity computation (numerical differentiation)         │
│  - Acceleration limits (enforce physical constraints)       │
│  - Gap interpolation (handle occlusion)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              STAGE 4: DELTA ACTION COMPUTATION               │
│  For each timestep t:                                        │
│    delta_pos[t] = pos[t] - pos[t-1]                        │
│    delta_rot[t] = rot[t] - rot[t-1]                        │
│    gripper_cmd[t] = compute_gripper_command(openness[t])   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               STAGE 5: QUALITY VALIDATION                    │
│  - Trajectory smoothness (jerk analysis)                    │
│  - Physical plausibility (velocity, acceleration limits)    │
│  - Temporal consistency (no teleportation)                  │
│  - Success detection (task completed?)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 STAGE 6: HDF5 EXPORT                        │
│  - Write timestep arrays to HDF5                            │
│  - Compress images (JPEG in HDF5)                           │
│  - Add metadata (task, success, duration)                   │
│  - Validate format (RoboMimic-compatible)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                OUTPUT: demo_001.hdf5                         │
│           Ready for robot training (Diffusion Policy, etc.)  │
└─────────────────────────────────────────────────────────────┘
```

---

## KEY ENGINEERING CHALLENGES

### 1. Coordinate Conversion (Biggest Challenge)

**Problem:** MediaPipe outputs normalized [0,1], robots need meters

**Solution A - Monocular Depth Estimation:**
```python
# Use pre-trained depth model (MiDaS, Depth-Anything)
depth_map = depth_model(frame)  # [H, W]
depth_at_wrist = depth_map[wrist_y, wrist_x]

# Convert normalized → 3D
x_metric = (wrist_x_norm - cx) * depth / fx
y_metric = (wrist_y_norm - cy) * depth / fy
z_metric = depth
```

**Solution B - Fixed Distance Assumption:**
```python
# Assume camera is 1.5m from workspace
CAMERA_DISTANCE = 1.5  # meters
WORKSPACE_WIDTH = 1.0  # meters

x_metric = (wrist_x_norm - 0.5) * WORKSPACE_WIDTH
y_metric = (wrist_y_norm - 0.5) * WORKSPACE_WIDTH
z_metric = CAMERA_DISTANCE  # Constant (approximate)
```

**Solution C - ArUco Marker Calibration:**
```python
# Place ArUco markers on table corners
# Detect markers → compute homography → get real-world coordinates
marker_corners_pixels = detect_aruco_markers(frame)
marker_corners_world = [[0,0,0], [0.5,0,0], [0.5,0.5,0], [0,0.5,0]]
H = cv2.findHomography(marker_corners_pixels, marker_corners_world)
wrist_world = transform(wrist_pixel, H)
```

**Recommendation:** Start with Solution B (simplest), add A later (accuracy)

---

### 2. Gripper Command Generation

**Problem:** Hand openness [0,1] → gripper command {-1, 0, 1}

**Solution:**
```python
def compute_gripper_command(openness_curr, openness_prev):
    """
    Convert continuous openness to discrete command

    Returns:
        -1: Close gripper
         0: Hold position
         1: Open gripper
    """
    THRESHOLD = 0.05  # Minimum change to trigger command

    delta = openness_curr - openness_prev

    if delta < -THRESHOLD:
        return -1  # Closing
    elif delta > THRESHOLD:
        return 1   # Opening
    else:
        return 0   # Holding
```

---

### 3. Temporal Consistency

**Problem:** Missing frames, occlusion, jitter

**Solution - Kalman Filter:**
```python
from filterpy.kalman import KalmanFilter

kf = KalmanFilter(dim_x=6, dim_z=3)
# State: [x, y, z, vx, vy, vz]
# Measurement: [x, y, z]

for measurement in wrist_positions:
    if is_valid(measurement):
        kf.update(measurement)
    kf.predict()

    smoothed_pos = kf.x[:3]
    smoothed_vel = kf.x[3:]
```

---

### 4. Reference Frame

**Problem:** Robot needs consistent world frame

**Solution:**
```python
# Detect table plane using RANSAC
table_plane = fit_plane_ransac(point_cloud)

# Define coordinate system:
# - Origin: Table center
# - Z-axis: Up (perpendicular to table)
# - X-axis: Camera forward direction
# - Y-axis: Right (right-hand rule)

# Transform all coordinates to this frame
wrist_world = transform_to_world_frame(wrist_camera, table_plane)
```

---

## DATA STRUCTURE SPECIFICATION

### HDF5 Layout (RoboMimic-Compatible):

```python
import h5py

with h5py.File('demo_001.hdf5', 'w') as f:
    # Create demo group
    demo = f.create_group('data/demo_0')

    # Observations
    obs = demo.create_group('obs')
    obs.create_dataset('images', data=frames, compression='gzip')
    obs.create_dataset('ee_pos', data=wrist_positions)
    obs.create_dataset('ee_quat', data=orientations)
    obs.create_dataset('gripper_qpos', data=gripper_openness)

    # Actions (delta commands)
    demo.create_dataset('actions', data=delta_actions)

    # Metadata
    demo.attrs['num_samples'] = num_timesteps
    f.attrs['total_demos'] = 1
    f.attrs['env_name'] = 'real_world'
```

---

## REUSABLE COMPONENTS

From current system:

```python
✅ PoseExtractor          # Keep as-is
✅ HandTracker            # Keep as-is
✅ ObjectDetector         # Keep as-is
✅ Video loading          # Keep as-is

🔄 Sampling logic         # Remove (process all frames)
❌ ActionClassifier       # Delete (wrong paradigm)
❌ RobotDataFormatter     # Replace with HDF5Writer
```

New components needed:

```python
➕ CoordinateConverter    # Normalized → metric
➕ TrajectorySmoothing    # Kalman filter
➕ DeltaActionComputer    # Compute control commands
➕ HDF5Writer             # Export to robot format
➕ QualityValidator       # Check trajectory quality
```

---

## IMPLEMENTATION PLAN

### Week 1: Core Pipeline
- [ ] Remove frame sampling (process all frames)
- [ ] Implement CoordinateConverter (fixed distance)
- [ ] Add TrajectorySmoothing (Kalman filter)
- [ ] Test with existing video (output wrist trajectory)

### Week 2: Robot Format
- [ ] Implement DeltaActionComputer
- [ ] Build HDF5Writer (RoboMimic format)
- [ ] Add metadata generation
- [ ] Validate against real robot dataset

### Week 3: Quality & Calibration
- [ ] Implement QualityValidator
- [ ] Add depth estimation (MiDaS)
- [ ] ArUco marker support (optional)
- [ ] Benchmark against ground truth

### Week 4: Production Ready
- [ ] Batch processing (100+ videos)
- [ ] Performance optimization
- [ ] Error handling
- [ ] Documentation + examples

---

## VALIDATION STRATEGY

### Test Against Real Datasets:

1. **Download RoboMimic dataset** (with videos)
2. **Process their videos with our system**
3. **Compare output HDF5 vs. their ground truth**
4. **Metrics:**
   - Position error (mm)
   - Trajectory smoothness
   - Gripper command accuracy
   - Format compatibility

### Success Criteria:
- ✅ Position error < 10mm
- ✅ Trajectory jerk < 5 m/s³
- ✅ HDF5 loads in RoboMimic without errors
- ✅ Can train policy on our data

---

## MARKET DIFFERENTIATION

**Our Advantage:**

1. **From video only** (no robot hardware needed)
2. **Automatic** (no manual labeling)
3. **Scalable** (process 1000s of videos)
4. **Format-agnostic** (output RoboMimic, RLDS, custom)

**vs. Traditional Collection:**
- Traditional: Robot teleop → record → 10-100 demos/day
- Us: Video collection → process → 1000+ demos/day

**10-100x faster data collection!**

---

## FILE STRUCTURE (New)

```
video_intelligence_system/
├── robot_pipeline/               # NEW
│   ├── coordinate_converter.py
│   ├── trajectory_smoother.py
│   ├── delta_action_computer.py
│   ├── hdf5_writer.py
│   ├── quality_validator.py
│   └── robot_pipeline.py        # Main orchestrator
├── core/                          # REUSE
│   └── extractors/
│       ├── pose_extractor.py     # Keep
│       ├── hand_tracker.py       # Keep
│       └── object_detector.py    # Keep
├── tests/
│   ├── test_coordinate_conversion.py
│   ├── test_hdf5_format.py
│   └── test_validation.py
└── datasets/
    ├── samples/                   # Real robot datasets
    └── validation/                # Ground truth comparisons
```

---

## DEPENDENCIES (Additional)

```python
# Coordinate conversion
pip install opencv-contrib-python  # ArUco markers

# Depth estimation (optional)
pip install torch timm
# MiDaS or Depth-Anything model

# Kalman filtering
pip install filterpy

# HDF5
pip install h5py

# Validation
pip install robomimic  # Load/test with real framework
```

---

## SUCCESS METRICS

### Technical:
- ✅ Output HDF5 compatible with RoboMimic/RLDS
- ✅ Position accuracy < 10mm
- ✅ Trajectory smoothness (jerk < 5 m/s³)
- ✅ Processing speed: 0.5-1x realtime

### Business:
- ✅ Generate 100 demos from video in <1 hour
- ✅ Data quality sufficient for policy training
- ✅ Cost: <$0.10 per demo (vs $50 for robot collection)

---

**NEXT STEP:** Start implementation (Week 1: Core Pipeline)
