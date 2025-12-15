# SYSTEM COHERENCE AUDIT
## Before Implementing Dual-Stream Consensus Architecture

**Philosophy**: "As automation advances, quality data will be important, so let's build with coherence"

---

## CURRENT SYSTEM INVENTORY

### Core Pipeline (Original Architecture)
```
core/
├── extractors/
│   ├── pose_extractor.py      # MediaPipe Pose (33 keypoints)
│   ├── hand_tracker.py         # MediaPipe Hands (21 landmarks)
│   └── object_detector.py      # YOLOv8 (object detection)
├── analyzers/
│   └── action_classifier.py   # Simple heuristic classifier
├── formatters/
│   └── robot_data_formatter.py # HDF5 export (RoboMimic format)
└── pipeline.py                 # Main orchestration
```

**Status**: ✅ Working foundation, but superseded by standalone scripts

---

### Standalone Processing Scripts (Current Workflow)
```
1. extract_everything.py              # Extract pose + hands + objects
2. add_color_analysis.py              # Add color information
3. compute_hand_orientation.py        # Add roll/pitch/yaw
4. convert_to_metric_3d.py           # Convert to metric coordinates
5. advanced_action_detection.py       # Physics-based action detection
```

**Status**: ✅ This is the ACTUAL pipeline being used (Videos #2-9)

**Issue**: Disconnected from `core/` architecture

---

### Analysis & Validation Tools
```
- analyze_velocity_pattern.py        # Debug velocity patterns
- analyze_twist_close.py             # Debug specific action
- analyze_video_activity.py          # Activity summary
- visualize_motion_trajectory.py     # Motion visualization (NEW)
```

**Status**: ✅ Useful debugging tools

---

### Detection System Evolution
```
1. compute_timestep_actions.py       # Original (basic)
2. enhanced_action_detection.py      # Iteration 1
3. improved_action_detection.py      # Iteration 2
4. advanced_action_detection.py      # Current (with rotation) ✅
5. hierarchical_detection_system.py  # Experimental (hierarchical)
```

**Status**: ⚠️ Multiple versions, unclear which is canonical

**Issue**: Need to consolidate or deprecate old versions

---

### Rule Systems (New - Not Integrated)
```
- locomotion_rules.py                # Running, walking, jumping rules
- contact_based_actions.py           # Writing, cutting, stirring rules
```

**Status**: ❌ NOT integrated into main pipeline

---

### New Architectural Documents (Not Implemented)
```
- VISION_BASED_APPROACH.md           # Vision AI integration plan
- AUTONOMOUS_VALIDATION_RULES.md     # Self-validation rules
- DUAL_STREAM_CONSENSUS_SYSTEM.md    # Dual-stream architecture
```

**Status**: 📋 Design documents, not code

---

## COHERENCE ISSUES IDENTIFIED

### Issue 1: Pipeline Fragmentation
**Problem**: `core/` architecture vs standalone scripts
```
Original:
  core/pipeline.py → Orchestrates everything

Current Reality:
  Manual workflow: Script 1 → Script 2 → Script 3 → Script 4 → Script 5
```

**Impact**: No single entry point, error-prone manual steps

---

### Issue 2: Multiple Detection Systems
**Problem**: 5 different action detection files
```
- compute_timestep_actions.py       (basic)
- enhanced_action_detection.py      (deprecated?)
- improved_action_detection.py      (deprecated?)
- advanced_action_detection.py      (current) ✅
- hierarchical_detection_system.py  (experimental)
```

**Impact**: Confusion about which to use, code duplication

---

### Issue 3: Disconnected Rule Systems
**Problem**: New rule systems not integrated
```
- locomotion_rules.py          # Exists but unused
- contact_based_actions.py     # Exists but unused
```

**Impact**: Incomplete action coverage, wasted effort

---

### Issue 4: No Unified Data Format
**Problem**: Different files use different schemas
```
- extraction.json           # From extract_everything.py
- with_colors.json          # From add_color_analysis.py
- with_orientation.json     # From compute_hand_orientation.py
- metric_3d.json           # From convert_to_metric_3d.py
- actions.json             # From advanced_action_detection.py
```

**Impact**: Intermediate files proliferate, hard to track data lineage

---

### Issue 5: Vision System Not Implemented
**Problem**: Vision-based detection documented but not coded
```
VISION_BASED_APPROACH.md exists
VisionActionClassifier.classify_action() is placeholder
```

**Impact**: Can't implement dual-stream architecture yet

---

## PROPOSED COHERENT ARCHITECTURE

### Goal: Single Unified Pipeline with Dual-Stream Detection

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED PIPELINE                         │
│                   (Coherent Entry Point)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: EXTRACTION (Multi-Modal)                         │
│  - Pose (MediaPipe)                                        │
│  - Hands (MediaPipe)                                       │
│  - Objects (YOLOv8)                                        │
│  - Colors (HSV analysis)                                   │
│  - Orientation (Roll/Pitch/Yaw)                           │
│  Output: unified_extraction.json                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: KINEMATIC ANALYSIS                               │
│  - Convert to metric 3D coordinates                        │
│  - Compute velocities & accelerations                      │
│  - Track hand trajectories                                 │
│  Output: kinematics.json                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│  STREAM A: PHYSICS       │    │  STREAM B: VISION        │
│  - Rule-based detection  │    │  - AI frame analysis     │
│  - Velocity thresholds   │    │  - Semantic recognition  │
│  - Hand state rules      │    │  - Visual reasoning      │
│  Output: physics.json    │    │  Output: vision.json     │
└──────────────────────────┘    └──────────────────────────┘
            │                               │
            └───────────────┬───────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: RECONCILIATION JUNCTION                          │
│  - Compare physics vs vision                               │
│  - Resolve conflicts                                       │
│  - Validate consistency                                    │
│  - Merge strengths                                         │
│  Output: reconciled_actions.json                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: ROBOT DATA EXPORT                                │
│  - Format: HDF5 (RoboMimic)                               │
│  - Includes: action labels + trajectories + metadata      │
│  Output: robot_data.hdf5                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION PLAN (Coherent Refactoring)

### Phase 1: Consolidate Existing Pipeline ✅
**Goal**: Unify standalone scripts into coherent pipeline

**Actions**:
1. Create `unified_pipeline.py` - single entry point
2. Integrate: extraction → colors → orientation → metric 3D
3. Deprecate old detection systems (keep only `advanced_action_detection.py`)
4. Move helper scripts to `tools/` directory

**Output**: One command processes video end-to-end

---

### Phase 2: Implement Vision Stream 🔄
**Goal**: Add vision-based action detection

**Actions**:
1. Create `vision_action_detector.py`
2. Implement frame extraction + analysis
3. Integrate Claude Vision API (or alternatives)
4. Return semantic action labels

**Output**: `VisionActionDetector` class working

---

### Phase 3: Build Reconciliation Junction 🔄
**Goal**: Implement dual-stream consensus

**Actions**:
1. Create `reconciliation_junction.py`
2. Implement conflict resolution logic
3. Add physics validation rules
4. Merge physics + vision outputs

**Output**: `ReconciliationJunction` class working

---

### Phase 4: Integrate Rule Systems 📋
**Goal**: Include locomotion & contact-based actions

**Actions**:
1. Integrate `locomotion_rules.py` into physics stream
2. Integrate `contact_based_actions.py` into physics stream
3. Test with full action taxonomy

**Output**: Complete action coverage

---

### Phase 5: Robot Data Export 📋
**Goal**: Clean HDF5 export for robot training

**Actions**:
1. Update `robot_data_formatter.py`
2. Export reconciled actions + kinematics
3. Include metadata (detection method, confidence)
4. Validate HDF5 format (RoboMimic compatible)

**Output**: Robot-ready training data

---

## FILE STRUCTURE (After Coherent Refactoring)

```
video_intelligence_system/
│
├── unified_pipeline.py              # 🆕 MAIN ENTRY POINT
│
├── core/                            # Core processing modules
│   ├── extraction/
│   │   ├── pose.py
│   │   ├── hands.py
│   │   ├── objects.py
│   │   ├── colors.py
│   │   └── orientation.py
│   │
│   ├── kinematics/
│   │   ├── metric_converter.py
│   │   └── velocity_computer.py
│   │
│   ├── detection/
│   │   ├── physics_detector.py      # 🆕 (from advanced_action_detection.py)
│   │   ├── vision_detector.py       # 🆕 NEW
│   │   └── reconciliation.py        # 🆕 NEW
│   │
│   ├── rules/
│   │   ├── manipulation_rules.py    # Hand actions
│   │   ├── locomotion_rules.py      # Body actions
│   │   └── contact_rules.py         # Tool use
│   │
│   └── export/
│       └── robot_formatter.py
│
├── tools/                           # Analysis & debugging tools
│   ├── visualize_trajectory.py
│   ├── analyze_velocity.py
│   └── debug_action.py
│
├── tests/                           # Validation tests
│   ├── test_physics_detector.py
│   ├── test_vision_detector.py
│   └── test_reconciliation.py
│
└── docs/                            # Documentation
    ├── ARCHITECTURE.md              # System architecture
    ├── API_REFERENCE.md             # API documentation
    ├── VALIDATION_METHODOLOGY.md    # Testing approach
    └── ACTION_TAXONOMY.md           # All supported actions
```

---

## DATA FLOW (Coherent)

### Input:
```
video.mp4
```

### Processing:
```python
from unified_pipeline import UnifiedPipeline

pipeline = UnifiedPipeline(
    enable_vision=True,           # Dual-stream mode
    enable_reconciliation=True    # Conflict resolution
)

result = pipeline.process('video.mp4')
```

### Output:
```
output/
├── video_unified_extraction.json   # All extracted features
├── video_kinematics.json           # Motion data
├── video_physics_detection.json    # Physics stream result
├── video_vision_detection.json     # Vision stream result
├── video_reconciled.json           # Final reconciled actions
└── video_robot_data.hdf5           # Robot training data
```

**Single coherent data lineage!**

---

## COHERENCE PRINCIPLES

### 1. Single Entry Point
**Before**: 5 separate scripts to run manually
**After**: `unified_pipeline.py` - one command

### 2. Clear Data Lineage
**Before**: 7 intermediate JSON files, unclear flow
**After**: Structured output directory, documented flow

### 3. Modular Components
**Before**: Monolithic scripts
**After**: Reusable modules in `core/`

### 4. No Code Duplication
**Before**: 5 detection systems
**After**: One canonical detector per stream

### 5. Testable
**Before**: No tests
**After**: Unit tests for each component

### 6. Documented
**Before**: Scattered markdown files
**After**: Organized `docs/` with clear architecture

---

## DECISION POINTS

### Question 1: Keep `core/` or Start Fresh?
**Option A**: Refactor existing `core/` directory
**Option B**: Build new structure, deprecate old `core/`

**Recommendation**: Option B
- Current `core/` is outdated
- Clean slate ensures coherence
- Can reference old code as needed

### Question 2: Vision Implementation Priority?
**Option A**: Implement full vision system first
**Option B**: Placeholder vision, implement reconciliation, then add vision

**Recommendation**: Option B
- Reconciliation logic is independent
- Can test with mock vision data
- Iterate vision implementation

### Question 3: Migration Strategy for Videos #2-9?
**Option A**: Reprocess all videos with new pipeline
**Option B**: Keep old results, use new pipeline for Video #10+

**Recommendation**: Option A (if time allows)
- Ensures consistency
- Validates new pipeline
- Clean comparison

---

## NEXT STEPS (Coherent Implementation)

### Immediate (Today):
1. ✅ Create `SYSTEM_COHERENCE_AUDIT.md` (this document)
2. 🔄 Create `unified_pipeline.py` skeleton
3. 🔄 Move `advanced_action_detection.py` → `core/detection/physics_detector.py`
4. 🔄 Create `core/detection/vision_detector.py` (placeholder)
5. 🔄 Create `core/detection/reconciliation.py`

### Short-term (This Week):
1. Implement full unified pipeline
2. Test on Video #9
3. Implement reconciliation junction
4. Document API

### Medium-term (Next Week):
1. Implement vision detector (Claude API)
2. Integrate locomotion & contact rules
3. Test on Video #10
4. Export robot data (HDF5)

---

## SUCCESS METRICS

### Coherence Achieved When:
- ✅ Single command processes video end-to-end
- ✅ Clear data lineage (input → extraction → detection → reconciliation → export)
- ✅ No duplicate code
- ✅ All components tested
- ✅ Documentation complete
- ✅ New developer can understand system in <1 hour

---

## USER'S PRINCIPLE

> "As automation advances, quality data will be important, so let's build with coherence"

**This audit ensures**:
- Clean architecture
- Maintainable codebase
- High-quality robot training data
- Scalable to 1000s of videos

**Ready to implement?** 🚀
