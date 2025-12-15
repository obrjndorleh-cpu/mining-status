# 🚨 CRITICAL BUG: Mining Loops Instead of Progressing

**Date:** 2025-12-14 20:00
**Severity:** CRITICAL - Blocking progress to 100 demos
**Impact:** Mining stuck at 11 demos, spinning wheels

---

## 🔍 Evidence (Data-Driven)

### Timestamp Analysis
```
EARLIER (17:50):
  Repost: Just keep trying... → 17:44:27
  Graston Technique Therapy  → 17:26:31
  Alice 3.1 demo             → 17:16:58

NOW (19:57) - 2 HOURS LATER:
  Repost: Just keep trying... → 19:56:32 ⚠️  RE-CREATED
  Graston Technique Therapy  → 19:55:36 ⚠️  RE-CREATED
  Alice 3.1 demo             → 19:54:54 ⚠️  RE-CREATED
```

### Download Log Analysis
```
Total downloads: 83
Unique videos: ~30
Duplicates found:

3x - Alice 3.1 demo
3x - Graston Technique Therapy
3x - YOU'VE BEEN OPENING BEER BOTTLES...
3x - FRONT LEVER TUTORIAL
3x - Repost: Just keep trying...
... (many more)
```

### Progress Metrics
```
2 hours elapsed
Expected: ~4 new demos (at 1.85/hour)
Actual: 0 new demos (11 → 11)
Behavior: Same 11 files overwritten multiple times
```

---

## 🐛 Root Cause

**Location:** `run_overnight_mining.py` lines 170-180

**Current Logic:**
```python
for category_name, queries in self.ACTION_CATEGORIES.items():
    for query_idx, query in enumerate(queries):
        # Only skips queries WITHIN SAME SESSION
        if (last_category == category_name and
            query_idx < last_query_index):
            continue  # Skip already processed THIS session

        mine_videos(query)  # Mines videos
```

**After all queries → LOOPS BACK to beginning!**

**What's Missing:**
- No tracking of which VIDEOS already processed
- No checking if HDF5 FILE already exists
- No deduplication across sessions/loops
- `--delete-after-extract` deletes videos, so can't check "already downloaded"

---

## 💥 Impact

**Current Behavior:**
1. Mining cycles through all query categories
2. Reaches end of all queries
3. Loops back to start
4. Re-downloads SAME videos
5. Overwrites SAME HDF5 files
6. Progress stuck at 11 demos forever

**Why 11 Demos:**
- First loop through all categories found 11 good videos
- Second loop re-downloads same 11 videos
- Third loop re-downloads same 11 videos
- Infinite loop, zero progress ❌

**Stats Are Misleading:**
```
Total accepted: 1,182  ← Includes duplicates!
Actual unique demos: 11  ← Real count
```

---

## ✅ Solution Options

### Option 1: Track Processed Videos (Recommended)
**Add video URL/title tracking:**
```python
# In run_overnight_mining.py
processed_videos = set()  # Load from persistent file

def should_process_video(video_url):
    if video_url in processed_videos:
        return False
    return True

# After processing:
processed_videos.add(video_url)
save_processed_list()
```

**Pros:** Clean, prevents all duplicates
**Cons:** Need persistent storage (JSON file)

### Option 2: Check HDF5 Existence Before Processing
**Before downloading:**
```python
hdf5_path = f"data_mine/permanent_data/hdf5/{video_name}.hdf5"
if os.path.exists(hdf5_path):
    print(f"⏭️  Skipping - already processed: {video_name}")
    continue
```

**Pros:** Simple, no extra storage
**Cons:** Relies on file names being identical

### Option 3: Expand Search Queries Instead of Looping
**Add more unique queries:**
```python
# Instead of looping same queries
# Add 1000+ unique queries
# Never repeat same query twice
```

**Pros:** More diverse data
**Cons:** Requires manual query expansion

---

## 🎯 Recommended Fix

**Implement Option 1 + Option 2 (belt and suspenders):**

1. **Track processed URLs** (persistent)
2. **Check HDF5 existence** (fast check)
3. **Both must pass** to process video

**Implementation:**
```python
class MiningDeduplicator:
    def __init__(self, processed_file='processed_videos.json'):
        self.processed_file = processed_file
        self.processed_urls = self.load_processed()
        self.hdf5_dir = Path('data_mine/permanent_data/hdf5')

    def load_processed(self):
        if Path(self.processed_file).exists():
            with open(self.processed_file) as f:
                return set(json.load(f))
        return set()

    def save_processed(self):
        with open(self.processed_file, 'w') as f:
            json.dump(list(self.processed_urls), f)

    def should_process(self, video_url, video_name):
        # Check 1: Already processed by URL?
        if video_url in self.processed_urls:
            return False

        # Check 2: HDF5 already exists?
        hdf5_path = self.hdf5_dir / f"{video_name}.hdf5"
        if hdf5_path.exists() and hdf5_path.stat().st_size > 1_000_000:
            return False  # Skip if >1MB (has RGB)

        return True

    def mark_processed(self, video_url):
        self.processed_urls.add(video_url)
        self.save_processed()
```

---

## 📊 Expected Outcome After Fix

**Before:**
- Progress: 11 → 11 → 11 (stuck)
- Behavior: Infinite loop, same videos

**After:**
- Progress: 11 → 15 → 20 → ... → 100
- Behavior: Only new videos processed
- Time to 100: ~48 hours (as projected)

---

## 🚀 Implementation Priority

**Priority:** URGENT - Blocking Gate 1 progress

**Steps:**
1. Stop current mining (PID 91922)
2. Implement deduplication
3. Test with 5 videos
4. Restart mining
5. Verify progress increases

**Time estimate:** 30-60 minutes to implement and test

---

## 📝 Testing Plan

1. Note current file count (11)
2. Implement fix
3. Run for 2 hours
4. Check file count → Should be >11
5. Check timestamps → Should all be new
6. Check duplicates → Should be zero

---

**Bottom line:** Mining is working (RGB ✓, extraction ✓) but stuck in infinite loop. Fix deduplication → progress resumes.
