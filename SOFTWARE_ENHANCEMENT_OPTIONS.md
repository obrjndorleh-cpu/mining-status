# SOFTWARE ENHANCEMENT OPTIONS

Analysis of additional libraries/tools that could improve the video intelligence system.

## Current Stack
- **Vision**: MediaPipe (pose/hands), YOLOv8 (objects), Depth-Anything V2 (depth)
- **Processing**: NumPy, OpenCV
- **Analysis**: Custom velocity-based action detection

---

## IDENTIFIED PROBLEMS & SOFTWARE SOLUTIONS

### Problem 1: Hand Motion vs Object Motion (Still Challenging)
**Issue**: Hard to distinguish hand pulling door vs hand reaching inside container

**Potential Solutions**:

#### Option A: Optical Flow Analysis
- **Library**: OpenCV Optical Flow (Farneback or Lucas-Kanade)
- **Benefit**: Track actual pixel movement in video - see if refrigerator door PIXELS move
- **Implementation**:
  ```python
  import cv2
  # Track if refrigerator bounding box changes position
  # If door opens, refrigerator bbox should expand/shift
  flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, ...)
  ```
- **Complexity**: Medium
- **Expected Impact**: HIGH - directly measures if door actually moves

#### Option B: SAM 2 (Segment Anything Model 2)
- **Library**: Meta's SAM 2 for video segmentation
- **Benefit**: Segment and track the DOOR separately from the fridge body
- **Implementation**:
  ```python
  from sam2.video_predictor import SAM2VideoPredictor
  # Segment refrigerator door as separate object
  # Track door rotation/opening
  ```
- **Complexity**: High (requires GPU, model loading)
- **Expected Impact**: VERY HIGH - precise door state tracking

#### Option C: 3D Scene Understanding
- **Library**: ZoeDepth or MiDaS (better depth) + 3D reconstruction
- **Benefit**: Build 3D model of scene, detect when door geometry changes
- **Complexity**: Very High
- **Expected Impact**: HIGH but expensive

---

### Problem 2: Action Segmentation Still Approximate

#### Option A: Temporal Action Localization (TAL) Models
- **Library**: ActionFormer, TriDet, or BMN
- **Benefit**: Deep learning models specifically trained for action boundaries
- **Dataset Needed**: Would need to fine-tune on our data
- **Complexity**: Very High (requires training)
- **Expected Impact**: HIGH for future, but needs labeled data

#### Option B: Change Point Detection
- **Library**: `ruptures` (Python library for change point detection)
- **Benefit**: Automatically detect when velocity/kinematic regime changes
- **Implementation**:
  ```python
  import ruptures as rpt
  # Detect regime changes in velocity signal
  algo = rpt.Pelt(model="rbf").fit(velocity_signal)
  breakpoints = algo.predict(pen=10)
  ```
- **Complexity**: Low
- **Expected Impact**: MEDIUM - better action boundary detection

---

### Problem 3: Object State Tracking (Is Door Open or Closed?)

#### Option A: Object State Classifiers
- **Library**: Train simple CNN on door states (open/closed)
- **Benefit**: Directly classify door state in each frame
- **Complexity**: Medium (need labeled examples)
- **Expected Impact**: HIGH - definitive door state

#### Option B: Pose Estimation for Objects
- **Library**: FoundationPose or MegaPose
- **Benefit**: Estimate 6D pose of objects including doors
- **Complexity**: Very High
- **Expected Impact**: VERY HIGH but complex

---

### Problem 4: Low Hand Tracking (63% in Video #2)

#### Option A: Hand4Whole (Whole-body Hand Tracking)
- **Library**: Hand4Whole from Meta
- **Benefit**: More robust hand tracking in challenging scenarios
- **Complexity**: Medium
- **Expected Impact**: MEDIUM - may improve occlusion handling

#### Option B: Multi-View Tracking
- **Approach**: Ask user to record from multiple angles
- **Benefit**: No occlusion issues
- **Complexity**: Low (software-wise) but requires user workflow change
- **Expected Impact**: HIGH but changes data collection

---

### Problem 5: Manipulation Detection Granularity

#### Option A: Contact Detection
- **Library**: Custom - detect when hand contacts object
- **Approach**:
  - Use depth + hand position + object bounding box
  - Detect when hand depth ≈ object depth AND hand inside object bbox
- **Complexity**: Low
- **Expected Impact**: MEDIUM - better grasp detection

#### Option B: Force Estimation
- **Library**: None - physics-based estimation
- **Approach**: Estimate applied force from hand acceleration
- **Complexity**: Medium
- **Expected Impact**: LOW - depth monocular is too imprecise

---

### Problem 6: Scale Calibration (Relative Units)

#### Option A: ArUco Markers
- **Library**: OpenCV ArUco
- **Benefit**: Place known-size marker in scene for scale
- **Implementation**:
  ```python
  import cv2.aruco as aruco
  # Detect marker, compute scale from known size
  ```
- **Complexity**: Low
- **Expected Impact**: HIGH - absolute metric scale
- **User Friction**: Requires placing marker in scene

#### Option B: Object Size Database
- **Library**: Custom database of common object sizes
- **Approach**: Detect "cup" → assume 8cm diameter → calibrate scale
- **Complexity**: Low
- **Expected Impact**: MEDIUM - approximate but no user friction

---

## RECOMMENDED IMMEDIATE ADDITIONS

### 1. **Optical Flow** (HIGHEST PRIORITY)
**Why**: Directly solves the "is door moving" problem
**Library**: OpenCV (already have it)
**Effort**: Low
**Impact**: High

### 2. **Change Point Detection** (HIGH PRIORITY)
**Why**: Better automatic action boundary detection
**Library**: `ruptures`
**Effort**: Low (pip install ruptures)
**Impact**: Medium-High

### 3. **Object Size Database** (MEDIUM PRIORITY)
**Why**: Enables metric scale without user friction
**Library**: Custom JSON file
**Effort**: Low
**Impact**: Medium

### 4. **Contact Detection** (MEDIUM PRIORITY)
**Why**: Better grasp/manipulation detection
**Library**: Custom algorithm
**Effort**: Medium
**Impact**: Medium

---

## FUTURE CONSIDERATIONS (After 10-Video Validation)

### 1. **SAM 2 for Door Segmentation**
- Very powerful but requires GPU
- Wait to see if optical flow is sufficient first

### 2. **Hand4Whole for Better Tracking**
- Only if hand tracking remains below 70% average

### 3. **Action Transformer Models**
- Only if we build a labeled dataset from the 10+ videos

---

## IMPLEMENTATION PLAN

### Phase 1: Low-Hanging Fruit (This Week)
1. ✅ Temporal clustering (DONE)
2. ⏳ Add optical flow for door motion detection
3. ⏳ Add ruptures for change point detection
4. ⏳ Object size database for scale calibration

### Phase 2: After 10-Video Validation (Next Week)
1. Evaluate if optical flow solved door detection
2. Consider SAM 2 if still issues
3. Implement contact detection for manipulation
4. Fine-tune thresholds based on aggregate data

### Phase 3: Advanced (Future)
1. Build labeled action dataset
2. Train action segmentation model
3. Implement 6D pose estimation if needed

---

## QUESTIONS FOR USER

1. **ArUco markers**: Are you willing to place a small printed marker (like a QR code) in scene for scale calibration? Or prefer automatic object-based calibration?

2. **GPU availability**: Do you have a GPU available? SAM 2 and advanced models need GPU.

3. **Multi-camera**: Would you consider recording from 2 angles simultaneously for better tracking?

4. **Door detection urgency**: Is door open/close detection the #1 priority, or is manipulation accuracy equally important?

---

## COST-BENEFIT SUMMARY

| Solution | Complexity | Time to Implement | Expected Impact | GPU Needed |
|----------|-----------|-------------------|-----------------|------------|
| Optical Flow | Low | 2-3 hours | High | No |
| ruptures (change points) | Low | 1 hour | Medium | No |
| Object size DB | Low | 2 hours | Medium | No |
| Contact detection | Medium | 4-6 hours | Medium | No |
| SAM 2 | High | 1-2 days | Very High | Yes |
| Hand4Whole | Medium | 4-6 hours | Medium | Yes (optional) |
| ArUco markers | Low | 1 hour | High | No |

**Recommendation**: Start with the top 3 (Optical Flow, ruptures, Object DB) - all can be done in one session, no GPU needed, high combined impact.
