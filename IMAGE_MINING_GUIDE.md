# 📸 IMAGE DATA MINING PIPELINE

Your complete image mining system is ready! Works just like video mining but simpler and faster.

---

## 🎯 **WHAT IT DOES**

```
Download Images → Score Quality → Extract Pose Data → Delete Images → Save Data
     ↓              ↓                    ↓                   ↓              ↓
  Unsplash       0-100 score        MediaPipe          Free space       HDF5
  Pexels        (≥70 accepted)     Pose + Hands      (Infinite!)      + JSON
```

---

## 🚀 **QUICK START**

### **1. Get API Keys (Free)**

**Unsplash** (Optional - works without but limited):
```bash
# Sign up: https://unsplash.com/developers
# Get access key
export UNSPLASH_ACCESS_KEY='your_key_here'
```

**Pexels** (Recommended - better reliability):
```bash
# Sign up: https://www.pexels.com/api/
# Get API key (free, 200 requests/hour)
export PEXELS_API_KEY='your_key_here'
```

### **2. Start Mining**

**Basic (test mode)**:
```bash
python run_image_mining.py --images-per-query 10 --threshold 70
```

**Full autonomous mode** (like video mining):
```bash
nohup python run_image_mining.py \
  --auto-process \
  --delete-after-extract \
  --threshold 70 \
  --images-per-query 30 \
  --sleep 30 \
  > image_mining.log 2>&1 &
```

---

## 📊 **COMPONENTS**

### **1. Image Downloader** (`image_downloader.py`)

Downloads images from free stock photo APIs.

**Supported sources**:
- ✅ Unsplash (free, high quality, no key needed but limited)
- ✅ Pexels (free with key, 200/hour)
- ⏳ Pixabay (coming soon)

**Test it**:
```bash
# Download 10 images
python image_downloader.py "person reaching" --max-images 10 --source pexels

# Check downloaded images
ls images/
```

### **2. Image Quality Scorer** (`image_quality_scorer.py`)

Scores images 0-100 based on:
- Pose detection (0-50 points)
- Hand detection (0-20 points)
- Lighting quality (0-15 points)
- Image clarity (0-10 points)
- Resolution (0-5 points)

**Test it**:
```bash
# Score an image
python image_quality_scorer.py images/some_image.jpg

# Output:
# Score: 85.0/100
# Rating: EXCELLENT
# Recommendation: Perfect for robot training
```

### **3. Image Extraction Pipeline** (`image_extraction_pipeline.py`)

Extracts robot training data from images:
- Body pose keypoints (33 landmarks × 4 values)
- Hand keypoints (21 per hand × 3 values)
- Saves to HDF5 + JSON

**Test it**:
```bash
# Extract data from image
python image_extraction_pipeline.py images/some_image.jpg

# Output files:
# - some_image.hdf5 (pose/hand data)
# - some_image.json (metadata)
```

### **4. Mining Orchestrator** (`run_image_mining.py`)

Ties everything together for 24/7 autonomous mining.

**Features**:
- ✅ Auto-download from 8 action categories
- ✅ Quality scoring (accept ≥70)
- ✅ Auto-extraction
- ✅ Auto-deletion (infinite mode)
- ✅ Cloud upload ready

---

## 🏭 **RUNNING 24/7**

```bash
# Start image mining in background
nohup python run_image_mining.py \
  --auto-process \
  --delete-after-extract \
  --threshold 70 \
  --images-per-query 30 \
  > image_mining.log 2>&1 &

echo $! > image_mining.pid
```

**Check status**:
```bash
# View log
tail -f image_mining.log

# Count images downloaded
ls data_mine_images/images/ | wc -l

# Count extracted data
ls data_mine_images/permanent_data/hdf5/ | wc -l
```

---

## ☁️ **CLOUD UPLOAD**

Upload to MongoDB Atlas (same as video data):

```bash
# Upload image data to cloud
python cloud_mining_setup.py --upload

# Specify custom data directory
python cloud_mining_setup.py --upload --data-dir data_mine_images/permanent_data
```

---

## 📈 **COMPARISON: IMAGE vs VIDEO MINING**

| Metric | Video Mining | Image Mining |
|--------|-------------|-------------|
| **Processing Speed** | ~30s/video | ~2s/image ⚡ |
| **Storage** | ~1MB/video | ~100KB/image |
| **Data Quality** | Temporal info ✅ | Static pose ✅ |
| **Rate Limits** | 70/hour (YouTube) | 200/hour (Pexels) |
| **Sources** | YouTube | Unsplash, Pexels, Pixabay |
| **Variety** | Limited angles | Diverse angles ✅ |

**Why use both?**
- Videos: Action sequences, temporal data
- Images: Diverse poses, faster mining, more variety

---

## 🎯 **ACTION CATEGORIES**

Both video and image mining use the same 8 categories:

1. **REACHING** - Person reaching for objects
2. **GRASPING** - Hand grasping/gripping
3. **LIFTING** - Lifting/raising objects
4. **PUSHING** - Pushing doors/objects
5. **PULLING** - Pulling ropes/drawers
6. **WAVING** - Hand waving gestures
7. **POINTING** - Pointing with finger
8. **HOLDING** - Holding/carrying objects

Each category has 5 search queries = **40 total queries**

---

## 💡 **BEST PRACTICES**

### **1. Use Both Video + Image Mining**

Run both simultaneously for maximum data diversity:

```bash
# Terminal 1: Video mining
python run_overnight_mining.py --auto-process --delete-after-extract

# Terminal 2: Image mining
python run_image_mining.py --auto-process --delete-after-extract
```

### **2. Set Up Pexels API Key**

Unsplash has strict rate limits. Pexels is more reliable:

1. Sign up: https://www.pexels.com/api/
2. Get API key (free)
3. Set environment variable:
   ```bash
   echo "export PEXELS_API_KEY='your_key'" >> ~/.zshrc
   source ~/.zshrc
   ```

### **3. Monitor Both Pipelines**

```bash
# Check both mining operations
ps aux | grep "run_.*_mining.py"

# Compare data collection
echo "Video data:" && ls data_mine/permanent_data/hdf5/ | wc -l
echo "Image data:" && ls data_mine_images/permanent_data/hdf5/ | wc -l
```

### **4. Upload to Cloud Regularly**

```bash
# Upload both video and image data
python cloud_mining_setup.py --upload --data-dir data_mine/permanent_data
python cloud_mining_setup.py --upload --data-dir data_mine_images/permanent_data
```

---

## 🔥 **EXPECTED PERFORMANCE**

With Pexels API (200 requests/hour):

**Hourly:**
- Images downloaded: ~200
- Acceptance rate: ~30%
- Quality images: ~60/hour
- Data extracted: ~6 MB/hour
- Images deleted: ~180 MB/hour freed

**Daily:**
- Quality images: ~1,440
- Data collected: ~144 MB
- Combined with video: **~2,000 samples/day!**

---

## 📱 **MONITORING**

All data goes to same MongoDB cloud:

```
Database: data_mining_empire
Collections:
  - robot_training_data (video + image data)
  - mining_statistics (combined stats)
```

Access from phone: https://cloud.mongodb.com

---

## ✅ **ADVANTAGES OF IMAGE MINING**

1. **Faster** - Process 10x more items per hour
2. **Diverse** - More pose variety from stock photos
3. **Higher quality** - Professional photography
4. **No temporal bias** - Single perfect poses
5. **Easier licensing** - Free stock photos

---

## 🚀 **YOUR COMPLETE DATA MINING EMPIRE**

```
┌─────────────────────────────────────────────┐
│         DATA MINING EMPIRE                  │
├─────────────────────────────────────────────┤
│                                             │
│  VIDEO MINING          IMAGE MINING         │
│  ├─ YouTube            ├─ Unsplash          │
│  ├─ 70/hour limit      ├─ 200/hour limit    │
│  ├─ ~30s/video         ├─ ~2s/image         │
│  └─ Temporal data      └─ Diverse poses     │
│                                             │
│  Both feed into:                            │
│  ├─ Quality Scoring (≥70)                   │
│  ├─ MediaPipe Extraction                    │
│  ├─ HDF5 Storage                            │
│  ├─ Auto-Delete (infinite space)            │
│  └─ MongoDB Cloud (access anywhere)         │
│                                             │
│  Combined Output:                           │
│  └─ ~2,000 quality samples/day              │
│                                             │
└─────────────────────────────────────────────┘
```

---

**Your image mining pipeline is ready to go! 🎉**

Start with Pexels API for best results, then scale to multiple sources.
