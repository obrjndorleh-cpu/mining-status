# 🚪 GATE 1 VALIDATION TOOLS

Created to validate data quality before proceeding to policy training.

---

## 📊 Tool 1: Mining Monitor

**Purpose:** Real-time monitoring of mining progress (macOS compatible)

### Usage

```bash
# Start monitoring (updates every 30 seconds)
python monitor_mining.py

# Custom update interval (e.g., 10 seconds)
python monitor_mining.py --interval 10

# Monitor different directory
python monitor_mining.py --hdf5-dir path/to/hdf5/files
```

### What It Shows

- Mining process status (running/stopped)
- Total HDF5 files count
- RGB demos count (>1 MB files)
- Pose-only demos count
- Progress bar to 100 RGB demos
- Most recent 10 RGB demos with timestamps
- Total storage used

### Example Output

```
======================================================================
MINING PROGRESS DASHBOARD
======================================================================
Time: 2025-12-13 16:45:30

Mining Status: 🟢 RUNNING

======================================================================
FILE STATISTICS
======================================================================
Total HDF5 files: 58
RGB demos (>1MB): 3
Pose-only demos: 55
Total storage: 124.3 MB

======================================================================
PROGRESS TO GATE 1 (100 RGB DEMOS)
======================================================================
[██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 3/100 (3.0%)

======================================================================
MOST RECENT RGB DEMOS (Last 10)
======================================================================
 1. [16:42:15] Opening_cabinet_door_tutorial.hdf5              28.1 MB
 2. [16:38:42] Pouring_water_into_glass.hdf5                   27.8 MB
 3. [16:35:20] Pulling_door_handle.hdf5                        28.4 MB

======================================================================
Press Ctrl+C to exit | Updates every 30 seconds
======================================================================
```

---

## ✅ Tool 2: Gate 1 Validator

**Purpose:** Validate 100 RGB demos against Gate 1 criteria

### Gate 1 Criteria

1. ✅ RGB frames at 224×224, 10+ FPS
2. ✅ Actions smooth (no jumps >10cm)
3. ✅ No NaN/Inf values
4. ✅ Format compatible with RoboMimic
5. ✅ Observation/action alignment correct

### Usage

```bash
# Validate all RGB demos (checks up to 100 random samples)
python gate1_validator.py data_mine/permanent_data/hdf5

# Validate specific number of samples
python gate1_validator.py data_mine/permanent_data/hdf5 --samples 50

# Custom output report
python gate1_validator.py data_mine/permanent_data/hdf5 --output my_report.json
```

### Example Output

```
======================================================================
GATE 1 VALIDATION
======================================================================

Found 100 RGB demos

Validating 100 random samples...

[1/100] Checking: Opening_cabinet_door_tutorial.hdf5...
  ✅ PASSED
[2/100] Checking: Pouring_water_into_glass.hdf5...
  ✅ PASSED
[3/100] Checking: Pulling_door_handle.hdf5...
  ❌ FAILED (2 issues)
...

======================================================================
GATE 1 VALIDATION SUMMARY
======================================================================
Total files checked: 100
Passed: 97 (97.0%)
Failed: 3 (3.0%)

✅ GATE 1: PASSED
   Ready to proceed to Gate 2 (policy training)

Common Issues:
  - Actions: Large jump detected: 2 files
  - Missing: obs/eef_vel: 1 file
```

### What It Checks

**Per File:**
- RGB frames present with correct shape (N, 224, 224, 3)
- RGB dtype is uint8
- FPS >= 10
- Actions have no NaN/Inf values
- No large jumps in actions (>10cm)
- All observations have no NaN/Inf
- Required datasets present
- Observation/action alignment (N obs, N-1 actions)

**Overall:**
- Pass rate >= 95% → GATE 1 PASSED
- Pass rate < 95% → GATE 1 FAILED (fix issues)

---

## 🔄 Workflow

### Step 1: Monitor Mining

```bash
# Terminal 1: Run monitor
python monitor_mining.py
```

Wait until you see **100 RGB demos**.

### Step 2: Run Gate 1 Validation

```bash
# Once you have 100 RGB demos
python gate1_validator.py data_mine/permanent_data/hdf5
```

### Step 3: Check Results

**If PASSED (>=95%):**
```
✅ GATE 1: PASSED
   Ready to proceed to Gate 2 (policy training)
```
→ Proceed to Phase 1 (train BC policy)

**If FAILED (<95%):**
```
❌ GATE 1: FAILED
   Pass rate: 92.0% (need >95%)
   Fix issues before proceeding

Common Issues:
  - Actions: Large jump detected: 5 files
  - RGB: Wrong resolution: 3 files
```
→ Fix identified issues, re-run validation

---

## 📋 Quick Reference

### Check Current RGB Count

```bash
# Count RGB demos (>1MB files)
ls -lh data_mine/permanent_data/hdf5/*.hdf5 | awk '$5 ~ /M/ {print}' | wc -l
```

### Check Mining Process

```bash
# See if mining is running
ps aux | grep "run_overnight_mining" | grep -v grep
```

### Check Mining Log

```bash
# View latest mining activity
tail -50 mining_rgb_fixed.log
```

### Visualize Random Demo

```bash
# Pick a random RGB demo and visualize
python visualize_hdf5.py data_mine/permanent_data/hdf5/demo_file.hdf5
```

---

## 🎯 Expected Timeline

**At 5.5% acceptance rate:**
- Videos analyzed per hour: ~20-40
- RGB demos per hour: ~1-2
- **Time to 100 demos: 24-72 hours**

**Progress Milestones:**
- 10 demos: 5-10 hours
- 50 demos: 12-36 hours
- 100 demos: 24-72 hours

---

## 🚀 After Gate 1 Passes

### Next Steps (Phase 1):

1. **Install RoboMimic**
   ```bash
   pip install robomimic
   ```

2. **Set up cloud GPU**
   - Sign up for Vast.ai or Lambda Labs
   - Get $10-20 credits

3. **Train first BC policy**
   ```bash
   python train_bc_policy.py data_mine/permanent_data/hdf5
   ```

4. **Validate learning (Gate 2)**
   - Training loss < 1.0
   - Position error < 10cm
   - Gripper error < 20%

---

## 💡 Tips

### Speed Up Mining

If you want faster results:
- Run multiple mining instances (parallel)
- Lower quality threshold temporarily (test only)
- Use shorter videos (faster processing)

### Storage Management

100 RGB demos = ~3 GB:
- Monitor disk space
- Archive old pose-only demos
- Use external drive if needed

### Debugging Failed Demos

If validation fails on specific files:
```bash
# Visualize the problematic demo
python visualize_hdf5.py data_mine/permanent_data/hdf5/problem_file.hdf5

# Check file details with h5py
python -c "import h5py; f = h5py.File('problem_file.hdf5', 'r'); print(list(f['data/demo_0'].keys()))"
```

---

**Tools ready! Start monitoring and let mining run.** 🚀
