# 🎯 QUALITY CONTROL WORKFLOW

Ensure only **clean, validated data** reaches your cloud database.

---

## 📋 **NEW WORKFLOW (Production-Ready)**

```
Video Download → Score → Process → Extract → DELETE Video
                                       ↓
                                  LOCAL HDF5
                                       ↓
                                  INSPECT ← You review here!
                                       ↓
                              Approve / Reject
                                       ↓
                                  APPROVED/
                                       ↓
                              UPLOAD TO CLOUD ☁️
```

**Key difference:** Human inspection before cloud upload!

---

## 🔍 **STEP 1: INSPECT DATA**

### **Option A: Manual Inspection (Careful)**

Review each file individually:

```bash
# Inspect single file
python data_inspector.py --file data_mine/permanent_data/hdf5/some_file.hdf5

# You'll see:
# - Validation results (✅ or ❌)
# - Data quality stats
# - Warnings (if any)
# - Recommendation
```

### **Option B: Batch Inspection (Faster)**

Review all uninspected files:

```bash
# Interactive batch inspection
python data_inspector.py --batch

# For each file, you'll see:
# - Validation results
# - Quality stats
# - Recommendation
#
# Then decide: [a]pprove / [r]eject / [s]kip
```

### **Option C: Auto-Approve (Production Mode)**

Auto-approve files that pass all checks:

```bash
# Auto-approve clean files, manual review for questionable ones
python data_inspector.py --batch --auto-approve --auto-reject

# This will:
# - ✅ Auto-approve files with no errors/warnings
# - ❌ Auto-reject files with critical errors
# - ⏸️  Ask you to manually review borderline cases
```

---

## ✅ **WHAT GETS CHECKED:**

### **Automatic Validation:**

1. **File Integrity**
   - Can file be opened?
   - All required datasets present?
   - No corruption?

2. **Pose Data Quality**
   - All 33 keypoints present?
   - No NaN or Inf values?
   - Average visibility > 30%?

3. **Hand Data** (if present)
   - Complete keypoint data?
   - Valid coordinate ranges?

4. **Metadata**
   - Action classification available?
   - Confidence scores present?

### **Recommendation Logic:**

- **APPROVE**: No errors, no warnings → Auto-uploadable
- **APPROVE_WITH_WARNINGS**: Valid but has minor issues → Review recommended
- **REJECT**: Critical errors or low quality → Don't upload

---

## 📁 **FILE ORGANIZATION**

After inspection, files are organized:

```
data_mine/permanent_data/
├── hdf5/              ← Uninspected (raw extracted data)
├── approved/          ← Ready for cloud upload ✅
├── rejected/          ← Quality issues, not uploaded ❌
├── json/              ← Metadata files
└── inspection_log.json ← History of all inspections
```

---

## ☁️ **STEP 2: UPLOAD APPROVED DATA**

### **Safe Upload (Only Approved Files)**

```bash
# Upload only inspected and approved data
python upload_approved_data.py

# This uploads from: data_mine/permanent_data/approved/
# Skips: Uninspected and rejected files
```

### **What Happens:**

1. Reads files from `approved/` directory
2. Validates they were inspected
3. Uploads to MongoDB Cloud
4. Shows upload summary

---

## 🔄 **DAILY WORKFLOW**

### **Option 1: Review Daily**

```bash
# Morning routine:
python data_inspector.py --batch --auto-approve --auto-reject
python upload_approved_data.py
```

### **Option 2: Review Weekly**

Let data accumulate, review in batch:

```bash
# Weekly cleanup:
python data_inspector.py --batch --auto-approve
python upload_approved_data.py

# Manually review borderline cases
```

---

## 📊 **CHECK INSPECTION STATUS**

```bash
# See what's been inspected
cat data_mine/permanent_data/inspection_log.json

# Count files by status
ls data_mine/permanent_data/hdf5/*.hdf5 | wc -l      # Uninspected
ls data_mine/permanent_data/approved/*.hdf5 | wc -l  # Approved
ls data_mine/permanent_data/rejected/*.hdf5 | wc -l  # Rejected
```

---

## 🎯 **EXAMPLE SESSION**

```bash
$ python data_inspector.py --batch

======================================================================
BATCH INSPECTION: 35 files
======================================================================

[1/35]
======================================================================
INSPECTING: video_001.hdf5
======================================================================

Validation: ✅ PASSED

Stats:
  • pose_keypoints: 33
  • avg_visibility: 0.85
  • visible_keypoints: 31
  • left_hand: True
  • right_hand: True

Metadata:
  • Action: reaching
  • Confidence: 0.92
  • Method: vision

✅ RECOMMENDATION: APPROVE for cloud upload

----------------------------------------------------------------------
Decision [a]pprove / [r]eject / [s]kip: a
✅ Approved: video_001.hdf5

[2/35]
======================================================================
INSPECTING: video_002.hdf5
======================================================================

Validation: ✅ PASSED

Warnings:
  ⚠️  Low average visibility: 0.28

Stats:
  • pose_keypoints: 33
  • avg_visibility: 0.28
  • visible_keypoints: 12
  • left_hand: False
  • right_hand: False

⚠️  RECOMMENDATION: APPROVE (with warnings)

----------------------------------------------------------------------
Decision [a]pprove / [r]eject / [s]kip: r
❌ Rejected: video_002.hdf5

...

======================================================================
INSPECTION COMPLETE
======================================================================

Inspection Summary:
  Total inspected: 35
  Approved: 28
  Rejected: 7

Approved files ready for cloud upload at:
  data_mine/permanent_data/approved
```

---

## 💡 **BEST PRACTICES**

### **1. Inspect Regularly**

Don't let uninspected files accumulate:

```bash
# Add to crontab (daily at 8am):
0 8 * * * cd /path/to/project && python data_inspector.py --batch --auto-approve
```

### **2. Review Rejected Files**

Check why files were rejected to improve mining:

```bash
ls data_mine/permanent_data/rejected/

# If too many rejections, adjust:
# - Quality threshold (currently 70)
# - Acceptance criteria
```

### **3. Backup Before Upload**

Keep local copies of approved data:

```bash
# Backup approved data before cloud upload
cp -r data_mine/permanent_data/approved/ backups/$(date +%Y%m%d)_approved/
python upload_approved_data.py
```

### **4. Monitor Cloud Storage**

Check what's in cloud regularly:

```bash
python cloud_mining_setup.py --status
```

---

## 🔒 **QUALITY GUARANTEES**

With this workflow, your cloud database contains:

✅ **Only validated files** (passed integrity checks)
✅ **Human-reviewed data** (or auto-approved if perfect)
✅ **No corrupted data** (automatic detection)
✅ **Consistent quality** (visibility thresholds)
✅ **Traceable history** (inspection log)

---

## 🚀 **INTEGRATION WITH EXISTING PIPELINE**

Your video mining continues as before:

```
Video Mining (24/7) → Extracts HDF5 → Saves to hdf5/
                                           ↓
                                     (accumulates)
                                           ↓
                      You inspect when ready → approved/
                                           ↓
                           Upload to cloud when clean
```

**Nothing changes in mining operation!** Just adds quality control before cloud.

---

## 📈 **EXPECTED WORKFLOW**

**Daily:**
- Mining runs 24/7 (no change)
- ~390 videos processed/day
- ~35 HDF5 files generated/day

**Weekly:**
- Inspect accumulated files: `python data_inspector.py --batch --auto-approve`
- Upload approved: `python upload_approved_data.py`
- Review rejected files
- ~245 files/week to cloud (assuming 30% rejection in inspection)

---

**Your data is now production-ready with quality control!** 🎉
