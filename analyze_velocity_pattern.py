"""
ANALYZE VELOCITY PATTERNS
Debug tool to understand why duplicate actions are detected
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

def analyze_velocity(metric_file):
    """
    Plot velocity over time to see patterns
    """
    print("📊 Analyzing velocity patterns...")

    with open(metric_file, 'r') as f:
        data = json.load(f)

    timesteps = data['timesteps']

    # Extract data
    timestamps = [ts['timestamp'] for ts in timesteps]
    velocities = np.array([ts['kinematics']['velocity'] for ts in timesteps])
    speeds = np.array([ts['kinematics']['speed'] for ts in timesteps])

    # Z velocity (depth - pull/push)
    z_vel = velocities[:, 2]

    # Create plot
    fig, axes = plt.subplots(3, 1, figsize=(15, 10))

    # Plot 1: Z velocity over time
    axes[0].plot(timestamps, z_vel, 'b-', linewidth=0.5)
    axes[0].axhline(y=-0.5, color='r', linestyle='--', label='OPEN threshold (-0.5)')
    axes[0].axhline(y=0.5, color='g', linestyle='--', label='CLOSE threshold (+0.5)')
    axes[0].axhline(y=0, color='k', linestyle='-', alpha=0.3)
    axes[0].set_ylabel('Z Velocity (depth)')
    axes[0].set_title('Z Velocity Over Time (Pull/Push Detection)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Speed over time
    axes[1].plot(timestamps, speeds, 'purple', linewidth=0.5)
    axes[1].axhline(y=1.0, color='r', linestyle='--', label='OPEN speed threshold')
    axes[1].axhline(y=0.8, color='g', linestyle='--', label='CLOSE speed threshold')
    axes[1].set_ylabel('Speed (magnitude)')
    axes[1].set_title('Hand Speed Over Time')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Detection zones
    axes[2].fill_between(timestamps, 0, 1,
                         where=(z_vel < -0.5) & (speeds > 1.0),
                         color='red', alpha=0.3, label='OPEN detected')
    axes[2].fill_between(timestamps, 0, 1,
                         where=(z_vel > 0.5) & (speeds > 0.8),
                         color='green', alpha=0.3, label='CLOSE detected')
    axes[2].set_ylabel('Detection')
    axes[2].set_xlabel('Time (seconds)')
    axes[2].set_title('Action Detection Zones')
    axes[2].legend()
    axes[2].set_ylim(0, 1)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('velocity_analysis.png', dpi=150)
    print("✅ Saved: velocity_analysis.png")

    # Print statistics
    print(f"\n📈 STATISTICS:")
    print(f"   Frames with Z-vel < -0.5 (OPEN trigger): {np.sum(z_vel < -0.5)}")
    print(f"   Frames with Z-vel > +0.5 (CLOSE trigger): {np.sum(z_vel > 0.5)}")
    print(f"   Frames with high speed (>1.0): {np.sum(speeds > 1.0)}")

    # Count how many separate regions trigger OPEN
    open_trigger = (z_vel < -0.5) & (speeds > 1.0)
    transitions = np.diff(open_trigger.astype(int))
    num_open_regions = np.sum(transitions == 1)

    close_trigger = (z_vel > 0.5) & (speeds > 0.8)
    transitions = np.diff(close_trigger.astype(int))
    num_close_regions = np.sum(transitions == 1)

    print(f"\n🎯 DETECTION REGIONS:")
    print(f"   Separate OPEN regions: {num_open_regions}")
    print(f"   Separate CLOSE regions: {num_close_regions}")
    print(f"\n💡 If you only opened once and closed once,")
    print(f"   but we detect {num_open_regions} open regions and {num_close_regions} close regions,")
    print(f"   then hand motion INSIDE fridge is triggering false detections!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze_velocity_pattern.py <metric_3d.json>")
        sys.exit(1)

    analyze_velocity(sys.argv[1])
