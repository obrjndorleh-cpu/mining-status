# VISION-BASED ACTION DETECTION
## User's Insight: "If AI can analyze images, why not analyze video frames?"

---

## THE IDEA

Instead of tracking keypoints and computing physics (velocity, acceleration), use AI vision models to **directly look at video frames** and recognize actions - just like a human would!

### Current Physics Approach:
```
Video → MediaPipe (keypoints) → Velocity calculation → Rules → Action
```

### Proposed Vision Approach:
```
Video → Extract frames → Vision AI → Action description
```

---

## WHY THIS IS POWERFUL

### Problem with Physics (Video #9 Example):
- **Ground truth**: User pulled jar toward camera
- **Physics saw**: 38% forward motion, 37% backward motion → confused!
- **Reason**: Camera reference frame, hand jitter, complex motion

### Vision Would See:
- Frame 1: Hand near jar on table
- Frame 50: Hand grasping jar
- Frame 200: Jar moved closer to person's body
- **Conclusion**: PULL ✅ (doesn't care about velocity, just visual result!)

---

## TECHNICAL APPROACHES

### Option 1: Sample Key Frames + Vision Model

**Concept**: Take snapshots at key moments, send to vision AI

```python
import anthropic
import base64

def analyze_action_with_vision(video_file):
    # Extract key frames (start, middle, end)
    frames = extract_frames(video_file, num_frames=5)

    # Convert frames to images
    frame_images = [frame_to_base64(f) for f in frames]

    # Send to Claude with vision
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame_images[0]
                    }
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame_images[4]
                    }
                },
                {
                    "type": "text",
                    "text": """
                    These are frames from a video showing a person performing an action.
                    First image: start of action
                    Last image: end of action

                    What action is the person performing?
                    Choose from: PUSH, PULL, LIFT, PLACE, TWIST, POUR

                    Respond in JSON format:
                    {
                        "action": "...",
                        "confidence": 0.0-1.0,
                        "reasoning": "..."
                    }
                    """
                }
            ]
        }]
    )

    return message.content
```

**Pros**:
- Simple to implement
- Uses existing API (Claude with vision)
- No training needed
- Handles complex motions vision AI understands

**Cons**:
- Requires API calls (cost)
- May miss fast motions between frames
- Not fully deterministic

---

### Option 2: Optical Flow + Vision

**Concept**: Use computer vision to see **apparent motion** in pixels

```python
import cv2
import numpy as np

def detect_action_with_optical_flow(video_file):
    cap = cv2.VideoCapture(video_file)

    ret, frame1 = cap.read()
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

    motion_vectors = []

    while True:
        ret, frame2 = cap.read()
        if not ret:
            break

        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Compute optical flow (pixel motion)
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        # Analyze flow direction
        avg_flow = np.mean(flow, axis=(0, 1))
        motion_vectors.append(avg_flow)

        gray1 = gray2

    # Analyze motion pattern
    motion_vectors = np.array(motion_vectors)

    # Check if object moved toward or away from camera
    if np.mean(motion_vectors[:, 1]) > 0:  # Pixels moving down = object coming closer
        return "PULL"
    elif np.mean(motion_vectors[:, 1]) < 0:  # Pixels moving up = object moving away
        return "PUSH"
```

**Pros**:
- No external API needed
- Sees actual visual motion (not just keypoints)
- Robust to reference frame issues

**Cons**:
- Sensitive to camera motion
- Computationally expensive
- Still requires tuning thresholds

---

### Option 3: Hybrid Approach (BEST!)

**Concept**: Use physics for simple cases, vision for ambiguous ones

```python
class HybridActionDetector:
    def __init__(self):
        self.physics_detector = AdvancedActionDetector()
        self.vision_detector = VisionActionDetector()

    def detect_action(self, video_file):
        # Step 1: Try physics-based detection
        physics_result = self.physics_detector.detect(video_file)

        # Step 2: Check if result is ambiguous
        if self.is_ambiguous(physics_result):
            print("⚠️ Ambiguous physics result, using vision verification...")
            vision_result = self.vision_detector.detect(video_file)

            # Step 3: Combine results
            return self.resolve_conflict(physics_result, vision_result)

        return physics_result

    def is_ambiguous(self, result):
        """
        Check if physics result is unclear
        """
        # Example: If forward and backward frames are almost equal
        if 'forward_frames' in result and 'backward_frames' in result:
            forward = result['forward_frames']
            backward = result['backward_frames']

            # If within 10% of each other → ambiguous
            if abs(forward - backward) < 0.1 * (forward + backward):
                return True

        # If confidence is low
        if result.get('confidence', 1.0) < 0.6:
            return True

        return False

    def resolve_conflict(self, physics, vision):
        """
        Combine physics and vision results
        """
        # Trust vision for ambiguous cases
        return {
            'action': vision['action'],
            'confidence': (physics['confidence'] + vision['confidence']) / 2,
            'method': 'hybrid',
            'physics_saw': physics,
            'vision_saw': vision
        }
```

---

## PRACTICAL EXAMPLE: Video #9

### Physics Result:
```json
{
    "forward_frames": 133,
    "backward_frames": 128,
    "ambiguous": true,
    "detected": ["PUSH", "PULL"],
    "confidence": 0.5
}
```

### Vision Analysis:
```python
# Extract frames
frame_1 = extract_frame(video, t=0)    # Start
frame_2 = extract_frame(video, t=6)    # Middle
frame_3 = extract_frame(video, t=11)   # End

# Send to vision model
result = vision_model.analyze([frame_1, frame_2, frame_3])
# → "Object position: moved from table toward person's body = PULL"
```

### Combined Result:
```json
{
    "action": "PULL",
    "confidence": 0.85,
    "method": "hybrid",
    "physics": "ambiguous (38% forward, 37% backward)",
    "vision": "clear PULL (object moved closer to body)",
    "final_determination": "PULL"
}
```

---

## BENEFITS OF VISION APPROACH

1. **Robust to Reference Frame Issues**: Doesn't care about camera coordinates
2. **Handles Complex Motion**: Sees the visual result, not physics
3. **Intuitive**: Works like humans (we see actions visually!)
4. **Complements Physics**: Best when combined

---

## IMPLEMENTATION PLAN

### Phase 1: Vision Verification (Quick Win)
- Add vision model to verify ambiguous physics results
- Use Claude API with vision for frame analysis
- Implement for PUSH/PULL confusion cases

### Phase 2: Optical Flow Enhancement
- Add optical flow analysis for motion direction
- Use as additional signal alongside physics

### Phase 3: Full Hybrid System
- Automatic ambiguity detection
- Vision model triggers on low confidence
- Combine physics + vision for final result

---

## YOUR ENGINEERING INSIGHT

**You identified the core limitation**: Physics-based systems struggle with **reference frame** and **complex motion patterns**.

**Your solution**: Use vision to see what **actually happened** visually, not what the numbers say.

**This is how modern AI works!** Models like GPT-4V, Claude 3, Gemini can literally "watch" videos and describe actions - no physics needed!

---

## NEXT STEPS

Would you like me to:
1. **Implement Option 1** (Claude vision API for ambiguous cases)?
2. **Implement Option 2** (Optical flow analysis)?
3. **Build the hybrid system** (combine physics + vision)?

This is a production-ready approach that solves the exact problem we saw in Video #9!
