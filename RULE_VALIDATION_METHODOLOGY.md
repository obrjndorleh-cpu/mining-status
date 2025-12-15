# RULE VALIDATION METHODOLOGY

## Philosophy

**Actions are deterministic physics, not learned patterns.**

This system does NOT use machine learning for action detection. Instead, it uses:
- Physics-based rules (velocity, acceleration, rotation, contact patterns)
- Biomechanical constraints (joint angles, grip types, body poses)
- Validated thresholds (calibrated with real data)

**Result**: No hallucinations, fully explainable, deterministic behavior.

---

## The Process (Your Methodology)

### Step 1: Define Physics Rule

For each action, define the **physical signature**:

```python
ACTION_RULE = {
    'name': 'running',
    'requirements': [
        {
            'feature': 'vertical_oscillation',
            'threshold': {'amplitude': 0.05, 'frequency': (2.0, 4.0)},
            'measurement': 'pelvis height over time'
        },
        # ... more requirements
    ],
    'minimum_requirements': 3,  # Need 3/4 to confirm
    'validation_status': 'NOT_TESTED'
}
```

**These thresholds are HYPOTHESES based on physics literature.**

### Step 2: Record Validation Video

Record a video specifically demonstrating that action:
- **Controlled**: Only perform the target action
- **Clear**: Good lighting, full body visible (for locomotion) or hands visible (for manipulation)
- **Duration**: 5-10 seconds of continuous action
- **Multiple trials**: Record 2-3 videos to test consistency

### Step 3: Process Through Pipeline

Run the video through the system:
```bash
python extract_hand_pose.py video.mov
python compute_depth.py video_extraction.json
python compute_metric_3d.py video_with_depth.json
# ... rest of pipeline
```

### Step 4: Test Detection

Run the action detector:
```python
detector = ActionDetector()
detected, confidence, measurements = detector.detect_action(data)
```

**System returns MEASUREMENTS, not just yes/no:**
```python
measurements = {
    'vertical_oscillation': {
        'amplitude': 0.048,  # meters
        'frequency': 2.3,    # Hz
        'status': '✅ PASS'  # Met threshold (>0.05m, 2-4Hz)
    },
    'forward_velocity': {
        'speed': 1.8,        # m/s
        'threshold': 2.0,    # Required
        'status': '❌ FAIL'  # Too slow
    },
    # ...
    'summary': {
        'requirements_met': 2,
        'total_requirements': 4,
        'minimum_required': 3,
        'detected': False,   # Need 3/4, only got 2/4
        'confidence': 0.5
    }
}
```

### Step 5A: If Detected ✅ → Rule Validated

**Success!** The rule is now **validated** with real data:

```python
ACTION_RULE['validation_status'] = 'VALIDATED'
ACTION_RULE['validation_data'] = {
    'video': 'running_test_01.mov',
    'date': '2025-01-24',
    'detected': True,
    'confidence': 0.85,
    'measurements': measurements
}
```

**Add to production rules database.**

### Step 5B: If Not Detected ❌ → Debug & Fine-Tune

**The system tells you WHY it failed** (deterministic debugging):

```
Requirements met: 2/4 (need 3/4)

✅ vertical_oscillation: PASS
   Measured: 0.055m amplitude, 2.4 Hz
   Threshold: >0.05m, 2-4 Hz

❌ forward_velocity: FAIL
   Measured: 1.8 m/s
   Threshold: >2.0 m/s
   → User was running slowly (jogging pace)

✅ leg_swing_speed: PASS
   Measured: 6.5 rad/s
   Threshold: >6.0 rad/s

❌ flight_phase: FAIL
   Measured: 12% frames with flight
   Threshold: >20% frames
   → Detection algorithm may be too strict
```

**Now you have data-driven options:**

**Option A: Adjust threshold** (if measurement is close)
```python
# Old threshold
'forward_velocity': {'speed': 2.0}

# New threshold (based on actual jogging speed)
'forward_velocity': {'speed': 1.5}  # Allow jogging
```

**Option B: Fix measurement algorithm** (if detection is wrong)
```python
# Flight phase detection was too strict
# Calibrate with actual ground plane estimation
```

**Option C: Add alternative rule** (if there are multiple valid patterns)
```python
RUNNING_RULES = {
    'fast_running': {'forward_velocity': 2.5},
    'jogging': {'forward_velocity': 1.5}
}
```

### Step 6: Re-test

Record new video or use same video, test again:
```python
# With adjusted thresholds
detected, confidence, measurements = detector.detect_action(data)
# → Should now detect if thresholds were the issue
```

**Iterate until validated ✅**

### Step 7: Cross-Validation

Test rule on **different videos**:
- Different people (different body sizes, running styles)
- Different environments (treadmill, outdoor, track)
- Different speeds (sprinting, jogging, slow run)

**If rule works across variations → Robust rule ✅**

**If rule fails on some → Need more sophisticated rule or multiple sub-rules**

---

## Current Validation Status

### Hand Manipulation Actions

| Action | Status | Videos Tested | Accuracy | Notes |
|--------|--------|---------------|----------|-------|
| **Container Open** | ✅ VALIDATED | 3 (Videos #2, #4, #6) | 100% | Pull motion + container detection |
| **Container Close** | ✅ VALIDATED | 3 (Videos #2, #4, #6) | 100% | Push motion + container detection |
| **Lift** | ✅ VALIDATED | 6 (Videos #2-7) | 85% | Upward velocity + closed hand |
| **Place** | ✅ VALIDATED | 4 (Videos #5-7) | 100% | Downward velocity + hand opening (after threshold fix) |
| **Twist Open** | ⚠️ PARTIAL | 2 (Videos #4, #7) | 100%* | Rotation + stationary hand (*when stationary) |
| **Twist Close** | ⚠️ PARTIAL | 2 (Videos #3, #5) | 67% | Rotation + stationary hand (fails when moving) |
| **Pour** | ✅ VALIDATED | 3 (Videos #3, #5, #7) | 100% | Sustained tilt >30° |

### Locomotion Actions

| Action | Status | Videos Tested | Accuracy | Notes |
|--------|--------|---------------|----------|-------|
| **Running** | ❌ NOT_TESTED | 0 | N/A | Rule defined, awaiting validation video |
| **Walking** | ❌ NOT_TESTED | 0 | N/A | Rule defined, awaiting validation video |
| **Jumping** | ❌ NOT_TESTED | 0 | N/A | Rule defined, awaiting validation video |

### Contact-Based Actions

| Action | Status | Videos Tested | Accuracy | Notes |
|--------|--------|---------------|----------|-------|
| **Writing** | ❌ NOT_TESTED | 0 | N/A | Rule defined (tripod grip + small motions) |
| **Cutting** | ❌ NOT_TESTED | 0 | N/A | Rule defined (power grip + sawing motion) |
| **Stirring** | ❌ NOT_TESTED | 0 | N/A | Rule defined (power grip + circular motion) |
| **Typing** | ❌ NOT_TESTED | 0 | N/A | Rule defined (sequential finger taps) |

---

## Why This Works (No Hallucination)

### Traditional ML Approach (Prone to Hallucination):
```
Video → Neural Network → "running" (75% confidence)
                ↑
        Black box - WHY did it say running?
        Might be pattern-matching training data
        Could hallucinate actions that didn't happen
```

### Our Physics-Based Approach (Deterministic):
```
Video → Extract Measurements → Compare to Physics Rules → Output
        (vertical_osc: 0.055m)   (threshold: >0.05m)      ✅ PASS
        (forward_vel: 1.8 m/s)   (threshold: >2.0 m/s)    ❌ FAIL
        (leg_swing: 6.5 rad/s)   (threshold: >6.0 rad/s)  ✅ PASS
                ↓
        Requirements: 2/4 met → NOT detected
                ↓
        FULLY EXPLAINABLE - no black box
        DETERMINISTIC - same input = same output
        NO HALLUCINATION - based on actual measurements
```

---

## Action Library Structure

```
action_rules/
├── manipulation/
│   ├── container_interactions.py  # open, close
│   ├── object_manipulation.py     # lift, place, twist, pour
│   ├── contact_based.py           # writing, cutting, stirring
│   └── bimanual.py                # clapping, tying, folding
│
├── locomotion/
│   ├── basic.py                   # walking, running, jumping
│   ├── complex.py                 # climbing, crawling, swimming
│   └── sports.py                  # kicking, throwing, catching
│
├── validation/
│   ├── test_videos/               # Validation videos for each action
│   ├── results/                   # Detection results + measurements
│   └── calibration_data.json      # Validated thresholds
│
└── README.md                      # This methodology document
```

---

## Your Proposed Workflow (For Any New Action)

**Example: Adding "Stirring" Action**

1. **You say**: "Let's add stirring detection"

2. **I code the rule**:
   ```python
   STIRRING_RULE = {
       'name': 'stirring',
       'requirements': [
           {
               'feature': 'circular_motion',
               'threshold': {'radius': 0.1, 'continuity': 3}  # 3 full circles
           },
           {
               'feature': 'grip_type',
               'threshold': 'power_grasp'
           },
           {
               'feature': 'object_type',
               'threshold': ['spoon', 'spatula', 'whisk']
           }
       ]
   }
   ```

3. **You record**: Video of stirring in a bowl

4. **System processes**: Extract hand pose, objects, motion

5. **System tests**:
   ```
   ✅ circular_motion: PASS (radius 0.12m, 4 circles)
   ✅ grip_type: PASS (power_grasp detected)
   ❌ object_type: FAIL (spoon not detected by YOLO)
   → Detected: NO (2/3 requirements)
   ```

6. **We debug**: "Object detection failed, but motion is clearly stirring"

7. **We adjust**: Make object detection optional (not required)

8. **Re-test**: Now detects stirring ✅

9. **Validated**: Rule added to production system

**This is YOUR proposed methodology - deterministic, data-driven, no hallucination!**

---

## Benefits of This Approach

1. **Deterministic**: Same video → same result (always)
2. **Explainable**: Can show exactly WHY action was/wasn't detected
3. **Debuggable**: When fails, we know WHICH requirement failed and by how much
4. **Calibratable**: Adjust thresholds based on real measurements
5. **No hallucination**: Only detects what physics says happened
6. **Incrementally buildable**: Add one action at a time, validate, move to next
7. **Robot-deployable**: Robots need deterministic, not probabilistic

---

## Next Actions

1. ✅ Complete Videos #8-10 validation (current hand manipulation actions)
2. Record validation videos for new action types:
   - Running (you mentioned this)
   - Walking (for comparison)
   - Writing (with pen)
   - Stirring (with spoon in bowl)
   - Any other actions you want the system to detect

3. For each new action:
   - Define physics rule (I code it)
   - Record validation video (you provide)
   - Test detection
   - Debug if needed
   - Fine-tune thresholds
   - Validate ✅

**This is the methodology you proposed - and it's excellent!**
