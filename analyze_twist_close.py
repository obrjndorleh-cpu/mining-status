"""
Analyze why twist close was not detected in Video #7
"""
import json
import numpy as np

# Load data
with open('test_video_07_full_extraction_with_colors_with_orientation.json', 'r') as f:
    extraction = json.load(f)

with open('test_video_07_metric_3d.json', 'r') as f:
    metric = json.load(f)

# Extract roll angles in 9-12s window (expected twist close time)
rolls = []
times = []
positions = []
openness_vals = []

for i, frame in enumerate(extraction['frames']):
    t = frame['timestamp']
    if 9.0 <= t <= 12.0:
        if frame['hands']['detected'] and frame['hands']['hands']:
            if 'orientation' in frame['hands']['hands'][0]:
                roll = frame['hands']['hands'][0]['orientation']['roll']
                rolls.append(roll)
                times.append(t)

                # Get position and openness from metric data
                pos = metric['timesteps'][i]['observations']['end_effector_pos_metric']
                op = metric['timesteps'][i]['observations']['gripper_openness']
                positions.append(pos)
                openness_vals.append(op)

if len(rolls) < 10:
    print("Insufficient data in 9-12s window")
    exit()

rolls = np.array(rolls)
times = np.array(times)
positions = np.array(positions)
openness_vals = np.array(openness_vals)

# Unwrap angles
rolls_rad = np.unwrap(np.radians(rolls))

# Compute roll rate
roll_rate = np.gradient(rolls_rad, times)

print("=" * 80)
print("TWIST CLOSE DETECTION ANALYSIS (Video #7, 9-12s window)")
print("=" * 80)

print(f"\nData availability:")
print(f"  Frames: {len(rolls)}")
print(f"  Roll angle range: {rolls.min():.1f}° to {rolls.max():.1f}°")
print(f"  Total rotation: {abs(rolls[-1] - rolls[0]):.1f}°")
print(f"  Average openness: {openness_vals.mean():.2f}")

# Check thresholds
TWIST_RATE_THRESHOLD = 2.0  # rad/s
MIN_ROTATION = np.radians(40)  # 40 degrees
MAX_HAND_MOVEMENT = 0.3  # meters

print(f"\nDetection thresholds:")
print(f"  Rotation rate: >{TWIST_RATE_THRESHOLD} rad/s ({np.degrees(TWIST_RATE_THRESHOLD):.1f}°/s)")
print(f"  Minimum rotation: {np.degrees(MIN_ROTATION):.1f}°")
print(f"  Maximum hand movement: {MAX_HAND_MOVEMENT}m")
print(f"  Hand must be closed: openness <0.3")

max_rate = np.abs(roll_rate).max()
print(f"\nActual measurements:")
print(f"  Max rotation rate: {max_rate:.3f} rad/s = {np.degrees(max_rate):.1f}°/s")

# Find periods with high rotation
high_rate_indices = np.where(np.abs(roll_rate) > TWIST_RATE_THRESHOLD)[0]
print(f"  Frames above rate threshold: {len(high_rate_indices)}/{len(rolls)}")

if len(high_rate_indices) == 0:
    print("\n" + "=" * 80)
    print("❌ DETERMINISTIC REASON: ROTATION RATE TOO SLOW")
    print("=" * 80)
    print(f"\nUser rotated at max {np.degrees(max_rate):.1f}°/s")
    print(f"System requires >{np.degrees(TWIST_RATE_THRESHOLD):.1f}°/s")
    print("\nThis is a SLOW, GENTLE twist close - below our threshold")
    print("NOT a hallucination - deterministic threshold failure!")

    # Calculate what happened
    total_rotation = abs(rolls_rad[-1] - rolls_rad[0])
    duration = times[-1] - times[0]
    avg_rate = total_rotation / duration

    print(f"\nActual twist:")
    print(f"  Total rotation: {np.degrees(total_rotation):.1f}°")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Average rate: {np.degrees(avg_rate):.1f}°/s")

    print("\n📊 DATA-DRIVEN RECOMMENDATION:")
    print(f"   Lower threshold from {np.degrees(TWIST_RATE_THRESHOLD):.1f}°/s to {np.degrees(avg_rate)*0.7:.1f}°/s")
    print("   OR: Add alternative detector for slow twists (total rotation >30° over 1-3s)")
else:
    print(f"\n✅ High rotation rate detected in {len(high_rate_indices)} frames")
    print("\nChecking other requirements...")

    # Check each high-rate period
    for idx in high_rate_indices[:3]:
        print(f"\n  Frame at t={times[idx]:.2f}s:")
        print(f"    Rate: {np.degrees(roll_rate[idx]):.1f}°/s")
        print(f"    Openness: {openness_vals[idx]:.2f} {'✅' if openness_vals[idx] < 0.3 else '❌ TOO OPEN'}")
