# 📊 HDF5 VISUALIZATION GUIDE

**Tool:** `visualize_hdf5.py`
**Purpose:** Continuously visualize RGB frames from any HDF5 file
**Your engineering partner built this for easy data inspection**

---

## 🚀 QUICK START

### Visualize Any HDF5 File
```bash
python visualize_hdf5.py <any_hdf5_file.hdf5>
```

**Output:** PNG image with 9 frames in 3×3 grid

---

## 💡 COMMON USAGE

### 1. Visualize Single File (9 frames)
```bash
python visualize_hdf5.py test_rgb_output.hdf5
```
**Creates:** `test_rgb_output_visualization.png`

### 2. More Frames (16 frames = 4×4 grid)
```bash
python visualize_hdf5.py test_rgb_output.hdf5 --frames 16
```

### 3. Custom Output Path
```bash
python visualize_hdf5.py data.hdf5 --output my_viz.png
```

### 4. Visualize ALL Files in Directory
```bash
python visualize_hdf5.py data_mine/permanent_data/hdf5/ --batch
```
**Creates:** `visualizations/` folder with all visualizations

---

## 📋 FULL OPTIONS

```bash
python visualize_hdf5.py [FILE/DIR] [OPTIONS]

Arguments:
  FILE/DIR              HDF5 file or directory path

Options:
  --frames, -f N        Number of frames to show (default: 9)
  --output, -o PATH     Custom output path
  --batch, -b           Process all HDF5 files in directory
  --help, -h            Show help message
```

---

## 📊 WHAT IT SHOWS

**Each visualization includes:**
- ✅ Title: Filename
- ✅ Metadata: Task, confidence, frame count
- ✅ Grid: 3×3 (9 frames) or 4×4 (16 frames)
- ✅ Timestamps: Frame number and time
- ✅ RGB frames: Actual visual data

**Example output:**
```
┌─────────────────────────────────────────┐
│ test_rgb_output                         │
│ Task: test | Confidence: 100% | 451 fr  │
├─────────┬─────────┬─────────────────────┤
│ Frame 0 │Frame 56 │ Frame 112           │
│ (0.0s)  │ (1.9s)  │ (3.7s)              │
├─────────┼─────────┼─────────────────────┤
│Frame 168│Frame 225│ Frame 281           │
│ (5.6s)  │ (7.5s)  │ (9.4s)              │
├─────────┼─────────┼─────────────────────┤
│Frame 337│Frame 393│ Frame 450           │
│(11.2s)  │(13.1s)  │ (15.0s)             │
└─────────┴─────────┴─────────────────────┘
```

---

## 🎯 USE CASES

### Quality Control
```bash
# Visualize new demo to verify RGB captured
python visualize_hdf5.py data_mine/permanent_data/hdf5/new_demo.hdf5
```

### Batch Inspection
```bash
# Visualize all approved demos
python visualize_hdf5.py data_mine/permanent_data/approved/ --batch
```

### Quick Check
```bash
# Just see 4 frames quickly
python visualize_hdf5.py demo.hdf5 --frames 4
```

### Full Timeline
```bash
# See 25 frames (5×5 grid) for detailed timeline
python visualize_hdf5.py demo.hdf5 --frames 25
```

---

## ✅ WHAT IT VALIDATES

**Automatically checks:**
1. ✅ RGB frames present in file
2. ✅ Correct shape (N, 224, 224, 3)
3. ✅ Valid data type (uint8)
4. ✅ Readable frames
5. ✅ Metadata present

**If file is pose-only:**
```
❌ No RGB frames found in this file!
   This appears to be a pose-only HDF5 file.
```

---

## 💡 TIPS

### Find Files to Visualize
```bash
# List all HDF5 files
ls data_mine/permanent_data/hdf5/*.hdf5

# Count files
ls data_mine/permanent_data/hdf5/*.hdf5 | wc -l

# Visualize most recent
ls -t data_mine/permanent_data/hdf5/*.hdf5 | head -1 | xargs python visualize_hdf5.py
```

### Batch Visualize Specific Pattern
```bash
# Only visualize files with "pull" in name
for f in data_mine/permanent_data/hdf5/*pull*.hdf5; do
    python visualize_hdf5.py "$f"
done
```

### Compare Before/After
```bash
# Visualize legacy (pose-only) - will show error
python visualize_hdf5.py data_mine/legacy_pose_only/old_demo.hdf5

# Visualize new (with RGB) - will show frames
python visualize_hdf5.py data_mine/permanent_data/hdf5/new_demo.hdf5
```

---

## 🎨 OUTPUT EXAMPLES

**File sizes:**
- 9 frames: ~400-500 KB
- 16 frames: ~700-900 KB
- 25 frames: ~1-1.5 MB

**Grid layouts:**
- 4 frames: 2×2
- 9 frames: 3×3 (recommended)
- 16 frames: 4×4
- 25 frames: 5×5

---

## 🚨 TROUBLESHOOTING

### Error: "No RGB frames found"
**Cause:** HDF5 file is pose-only (old format)
**Solution:** This file was created before RGB implementation. Only new files have RGB.

### Error: "File not found"
**Cause:** Wrong path
**Solution:** Use full path or check file exists:
```bash
ls -l your_file.hdf5
```

### Error: "Module not found: PIL"
**Cause:** Pillow not installed
**Solution:**
```bash
pip install Pillow
```

---

## 📊 WORKFLOW INTEGRATION

### After Mining
```bash
# Visualize latest mined data
python visualize_hdf5.py data_mine/permanent_data/hdf5/ --batch --frames 9
```

### Before Cloud Upload
```bash
# Inspect all approved files
python visualize_hdf5.py data_mine/permanent_data/approved/ --batch
```

### Quality Check
```bash
# Visualize random sample
ls data_mine/permanent_data/hdf5/*.hdf5 | shuf | head -5 | while read f; do
    python visualize_hdf5.py "$f"
done
```

---

## ✅ SUMMARY

**You now have:**
- ✅ Easy visualization tool (`visualize_hdf5.py`)
- ✅ Works on any HDF5 file
- ✅ Batch processing for directories
- ✅ Automatic quality validation
- ✅ Visual proof RGB data works

**Usage:**
```bash
# Single file
python visualize_hdf5.py demo.hdf5

# All files in folder
python visualize_hdf5.py data_mine/permanent_data/hdf5/ --batch
```

**Your engineering partner: Making data inspection easy.** 💪
