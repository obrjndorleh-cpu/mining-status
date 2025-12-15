# 🎯 24/7 DATA MINING - QUICK START GUIDE

Your complete robot training data mining operation is ready!

## 🚀 THREE WAYS TO START

### Option 1: Quick Test (5 minutes)
Test the system with a small search:

```bash
python auto_dataset_curator.py \
    --queries "pouring water shorts" "opening door shorts" \
    --max-per-query 5 \
    --max-duration 15 \
    --threshold 60
```

**What happens:**
- Searches YouTube for 2 queries
- Downloads up to 5 videos per query
- Scores each video (0-100)
- Keeps only videos scoring >60
- Shows you results

---

### Option 2: Overnight Mining (8-12 hours)
Let it run while you sleep:

```bash
# Start mining operation
nohup python run_overnight_mining.py \
    --output-dir data_mine \
    --threshold 70 \
    --videos-per-query 10 \
    --max-duration 20 \
    --sleep 30 \
    > mining.log 2>&1 &

# Check it's running
tail -f mining.log

# Press Ctrl+C to stop watching (mining continues in background)
```

**What happens:**
- Runs continuously in background
- Cycles through 10 action categories (opening, closing, pouring, etc.)
- Downloads 10 videos per search query
- Keeps only high-quality videos (>70/100)
- Saves all progress to `data_mine/`
- Logs everything to `mining.log`

**To stop:**
```bash
# Find the process
ps aux | grep run_overnight_mining

# Kill it (replace PID with actual process ID)
kill <PID>
```

---

### Option 3: 24/7 Production Mining
Maximum data generation:

```bash
# Install screen for persistent sessions
# (Already installed on macOS)

# Start screen session
screen -S mining

# Inside screen, start mining
python run_overnight_mining.py \
    --output-dir production_data \
    --threshold 70 \
    --videos-per-query 20 \
    --max-duration 20 \
    --sleep 60

# Detach from screen (mining continues)
# Press: Ctrl+A, then D

# Later, reattach to check progress
screen -r mining

# Or view logs
tail -f production_data/curation_results.json
```

---

## 📊 CHECKING YOUR RESULTS

### View Mining Statistics
```bash
python -c "
import json
with open('data_mine/curation_results.json', 'r') as f:
    data = json.load(f)
    print(f'Videos analyzed: {data[\"videos_analyzed\"]}')
    print(f'Videos accepted: {data[\"videos_accepted\"]}')
    print(f'Acceptance rate: {data[\"acceptance_rate\"]:.1%}')
    print(f'Curated videos: {len(data[\"curated_videos\"])}')
"
```

### List All Quality Videos
```bash
ls -lh data_mine/videos/*.mp4 | head -20
```

### Check Quality Scores
```bash
python video_quality_scorer.py data_mine/videos/*.mp4 --threshold 70
```

---

## 💾 MONGODB SETUP (OPTIONAL BUT RECOMMENDED)

MongoDB gives you powerful querying:
- "Show me all opening actions with quality >80"
- "How many pouring samples do I have?"
- "What's my acceptance rate per action category?"

### Install MongoDB (if not installed)
```bash
# macOS
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community
```

### Use MongoDB Storage
```python
from mongodb_storage import RobotDataStorage

# Connect to MongoDB
storage = RobotDataStorage()

# Store video analysis
storage.store_video_analysis(video_path, quality_result, search_query, accepted=True)

# Store robot data
storage.store_robot_data(video_path, robot_data)

# Query by action
opening_videos = storage.get_videos_by_action('opening', min_quality=80)

# Get statistics
storage.print_statistics()

# Export dataset manifest
storage.export_dataset_manifest('my_dataset_manifest.json')
```

---

## 📈 EXPECTED RESULTS

Based on our testing:

**Acceptance Rate:** ~30-50%
- 100 videos analyzed → 30-50 quality videos
- Depends on search queries and action types

**Mining Speed:**
- ~10 videos/hour (with 30s sleep between queries)
- Overnight (8 hours) → 80 videos analyzed → ~30 quality videos
- 24/7 week → ~1,680 videos analyzed → ~600 quality videos

**Action Categories:**
Your miner searches for:
1. Opening (refrigerators, doors, cabinets, drawers, bottles)
2. Closing (doors, cabinets, drawers)
3. Pouring (water, liquids)
4. Grasping (picking up objects)
5. Placing (setting down objects)
6. Pushing (buttons, doors)
7. Pulling (handles, drawers, levers)
8. Twisting (bottle caps, knobs)
9. Sliding (doors, objects)
10. Lifting (ergonomic lifting)

---

## 🎯 BUILDING YOUR PILOT DATASET

**Goal:** 1,000 quality videos (100 per action category)

**Timeline:**
- Week 1: Run overnight mining every night
- Week 2: Collect ~200-300 quality videos
- Week 3-4: Continue mining to reach 1,000 videos
- Month 2: Process all through full pipeline → HDF5 dataset

**Commands:**
```bash
# Start mining for pilot dataset
python run_overnight_mining.py \
    --output-dir pilot_dataset \
    --threshold 70 \
    --videos-per-query 20

# Leave running 24/7 for 2-3 weeks
```

---

## 🔥 TROUBLESHOOTING

### "Rate limited by YouTube"
- Increase `--sleep` parameter (try 60 or 120 seconds)
- Use different search queries
- Wait a few hours and resume

### "Low acceptance rate"
- Lower `--threshold` (try 60 instead of 70)
- Adjust `--max-duration` (try 10-25 seconds)
- Different search queries get different quality

### "Download failed"
- Check internet connection
- Clear browser cookies: `rm -rf ~/Library/Application\ Support/Google/Chrome/Default/Cookies`
- Restart YouTube downloader

### "MongoDB connection failed"
- System works fine without MongoDB (uses JSON files)
- Or install MongoDB: `brew install mongodb-community`

---

## 📊 WHAT YOU'LL HAVE

After running 24/7 for a week:

```
data_mine/
├── videos/              # ~600 quality video files
├── robot_data/          # Processed robot training data (if you enable --process)
├── curation_results.json    # Statistics and metadata
└── mining_log.json      # Mining operation history
```

**This is your raw data mine!**

Next step: Process through full pipeline to generate HDF5 training dataset.

---

## 🚀 NEXT STEPS

1. **Start mining now:** `python run_overnight_mining.py`
2. **Let it run:** Overnight or 24/7
3. **Check results tomorrow:** See how many quality videos you mined
4. **Scale up:** Once working, let it run for weeks
5. **Build dataset:** Process all quality videos → HDF5 → Product!

---

## 💡 PRO TIPS

1. **Start small:** Test with 5-10 videos first to verify system works
2. **Monitor first hour:** Watch the mining.log to ensure no errors
3. **Check acceptance rate:** If <20%, adjust search queries or threshold
4. **Be patient:** Quality data takes time, but automation does the work!
5. **Save everything:** Never delete mined videos - storage is cheap!

---

**Ready to start? Pick an option above and let the mining begin!** ⛏️✨
