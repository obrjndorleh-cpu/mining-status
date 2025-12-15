# Quick Start Guide

Get up and running in 5 minutes!

---

## Installation

### 1. Create Virtual Environment

```bash
cd /Users/swiftsyn/video_intelligence_system
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: First installation will download:
- MediaPipe models (~50MB)
- YOLOv8 model (~6MB)
- PyTorch (~2GB)

This may take 5-10 minutes depending on your connection.

---

## Test the System

### Quick Test (No Video Needed)

```bash
python3 core/pipeline.py
```

Should output: `✅ Pipeline initialized`

### Full Test (With Video)

1. **Get a test video** - any video showing a person doing something with their hands
   - Example: Recording yourself picking up a cup
   - Or download a demo from YouTube

2. **Run the pipeline**:

```bash
python3 examples/basic_usage.py
```

---

## What Happens During Processing

```
📹 STEP 1: Loading video
👤 STEP 2: Extracting human poses (MediaPipe)
✋ STEP 3: Tracking hands (21 landmarks)
📦 STEP 4: Detecting objects (YOLO)
🏃 STEP 5: Analyzing motion patterns
🏷️  STEP 6: Auto-labeling actions
📊 STEP 7: Computing quality metrics
✅ DONE: Structured JSON output
```

---

## Expected Output

```json
{
  "video_metadata": {...},
  "actions": [
    {
      "label": "reach",
      "start_time": 0.0,
      "end_time": 1.2,
      "confidence": 0.94,
      "target_object": "cup"
    },
    {
      "label": "grasp",
      "start_time": 1.2,
      "end_time": 2.1,
      "confidence": 0.88,
      "grasp_type": "pinch"
    }
  ],
  "quality_score": 87
}
```

---

## Troubleshooting

### "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "YOLO model not found"
The YOLOv8 model downloads automatically on first run. Check your internet connection.

### "Video codec not supported"
Convert video to MP4:
```bash
ffmpeg -i input.mov -c:v libx264 output.mp4
```

---

## Next Steps

1. ✅ Test with your own videos
2. ✅ Experiment with different actions
3. ✅ Check quality scores
4. ✅ Review JSON output structure

---

## Performance

**M4 Mac Mini (16GB RAM)**:
- Processing speed: ~0.2x realtime (5min video = 25min processing)
- Memory usage: ~4GB
- Runs entirely locally - no API calls

**Optimization tips**:
- Lower `sample_fps` for faster processing
- Use YOLOv8n (nano) model for speed
- Process shorter clips first

---

**Ready to build the robot training data pipeline!** 🚀
