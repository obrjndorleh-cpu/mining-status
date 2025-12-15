"""
MOTION TRAJECTORY VISUALIZER

Visualizes the motion trajectory and velocity patterns for a video
Shows exactly what the physics-based detector "sees"
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys


def visualize_motion(metric_file, actions_file, extraction_file):
    """
    Create comprehensive visualization of motion trajectory
    """
    # Load data
    with open(metric_file, 'r') as f:
        metric_data = json.load(f)

    with open(actions_file, 'r') as f:
        actions_data = json.load(f)

    with open(extraction_file, 'r') as f:
        extraction_data = json.load(f)

    timesteps = metric_data['timesteps']
    actions = actions_data['actions']

    # Extract data
    timestamps = np.array([ts['timestamp'] for ts in timesteps])
    positions = np.array([ts['observations']['end_effector_pos_metric'] for ts in timesteps])
    velocities = np.array([ts['kinematics']['velocity'] for ts in timesteps])
    speeds = np.array([ts['kinematics']['speed'] for ts in timesteps])
    openness = np.array([ts['observations']['gripper_openness'] for ts in timesteps])

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))

    # 1. 3D Trajectory Plot
    ax1 = fig.add_subplot(3, 3, 1, projection='3d')
    ax1.plot(positions[:, 0], positions[:, 2], positions[:, 1], 'b-', linewidth=1, alpha=0.5)
    ax1.scatter(positions[0, 0], positions[0, 2], positions[0, 1], c='green', s=100, label='Start', marker='o')
    ax1.scatter(positions[-1, 0], positions[-1, 2], positions[-1, 1], c='red', s=100, label='End', marker='X')
    ax1.set_xlabel('X (lateral)')
    ax1.set_ylabel('Z (forward/back)')
    ax1.set_zlabel('Y (vertical)')
    ax1.set_title('3D Hand Trajectory')
    ax1.legend()

    # 2. X-Y Top View
    ax2 = fig.add_subplot(3, 3, 2)
    ax2.plot(positions[:, 0], positions[:, 2], 'b-', linewidth=1)
    ax2.scatter(positions[0, 0], positions[0, 2], c='green', s=100, label='Start', marker='o')
    ax2.scatter(positions[-1, 0], positions[-1, 2], c='red', s=100, label='End', marker='X')
    ax2.set_xlabel('X (lateral - left/right)')
    ax2.set_ylabel('Z (forward/back)')
    ax2.set_title('Top View (Bird\'s Eye)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax2.axvline(x=0, color='k', linestyle='--', alpha=0.3)

    # 3. Y-Z Side View
    ax3 = fig.add_subplot(3, 3, 3)
    ax3.plot(positions[:, 2], positions[:, 1], 'b-', linewidth=1)
    ax3.scatter(positions[0, 2], positions[0, 1], c='green', s=100, label='Start', marker='o')
    ax3.scatter(positions[-1, 2], positions[-1, 1], c='red', s=100, label='End', marker='X')
    ax3.set_xlabel('Z (forward/back)')
    ax3.set_ylabel('Y (vertical - up/down)')
    ax3.set_title('Side View (Profile)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax3.axvline(x=0, color='k', linestyle='--', alpha=0.3)

    # 4. Z-Velocity Over Time (FORWARD/BACKWARD)
    ax4 = fig.add_subplot(3, 3, 4)
    ax4.plot(timestamps, velocities[:, 2], 'b-', linewidth=1, label='Z-velocity')
    ax4.axhline(y=0, color='k', linestyle='-', linewidth=1)
    ax4.axhline(y=0.3, color='g', linestyle='--', alpha=0.5, label='Backward threshold (PULL)')
    ax4.axhline(y=-0.3, color='r', linestyle='--', alpha=0.5, label='Forward threshold (PUSH)')
    ax4.fill_between(timestamps, 0, velocities[:, 2], where=(velocities[:, 2] > 0.3), alpha=0.3, color='green', label='Backward motion')
    ax4.fill_between(timestamps, 0, velocities[:, 2], where=(velocities[:, 2] < -0.3), alpha=0.3, color='red', label='Forward motion')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Z-Velocity (forward/back)')
    ax4.set_title('Z-Velocity: PUSH (negative) vs PULL (positive)')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=8)

    # 5. X-Velocity Over Time (LATERAL)
    ax5 = fig.add_subplot(3, 3, 5)
    ax5.plot(timestamps, velocities[:, 0], 'purple', linewidth=1)
    ax5.axhline(y=0, color='k', linestyle='-', linewidth=1)
    ax5.axhline(y=0.4, color='purple', linestyle='--', alpha=0.5, label='Right threshold')
    ax5.axhline(y=-0.4, color='orange', linestyle='--', alpha=0.5, label='Left threshold')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('X-Velocity (lateral)')
    ax5.set_title('X-Velocity: Left (negative) vs Right (positive)')
    ax5.grid(True, alpha=0.3)
    ax5.legend(fontsize=8)

    # 6. Y-Velocity Over Time (VERTICAL)
    ax6 = fig.add_subplot(3, 3, 6)
    ax6.plot(timestamps, velocities[:, 1], 'brown', linewidth=1)
    ax6.axhline(y=0, color='k', linestyle='-', linewidth=1)
    ax6.axhline(y=0.3, color='orange', linestyle='--', alpha=0.5, label='Downward threshold (PLACE)')
    ax6.axhline(y=-0.5, color='blue', linestyle='--', alpha=0.5, label='Upward threshold (LIFT)')
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('Y-Velocity (vertical)')
    ax6.set_title('Y-Velocity: Up (negative) vs Down (positive)')
    ax6.grid(True, alpha=0.3)
    ax6.legend(fontsize=8)

    # 7. Speed Over Time
    ax7 = fig.add_subplot(3, 3, 7)
    ax7.plot(timestamps, speeds, 'darkblue', linewidth=1.5, label='Speed')
    ax7.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Motion threshold')
    ax7.fill_between(timestamps, 0, speeds, where=(speeds > 0.5), alpha=0.3, color='blue')
    ax7.set_xlabel('Time (s)')
    ax7.set_ylabel('Speed (magnitude)')
    ax7.set_title('Overall Speed')
    ax7.grid(True, alpha=0.3)
    ax7.legend()

    # 8. Hand Openness Over Time
    ax8 = fig.add_subplot(3, 3, 8)
    ax8.plot(timestamps, openness, 'darkgreen', linewidth=1.5, label='Openness')
    ax8.axhline(y=0.3, color='r', linestyle='--', alpha=0.5, label='Grasping threshold')
    ax8.axhline(y=0.4, color='orange', linestyle='--', alpha=0.5, label='PULL threshold')
    ax8.fill_between(timestamps, 0, openness, where=(openness < 0.3), alpha=0.3, color='green', label='Closed (grasping)')
    ax8.fill_between(timestamps, openness, 1, where=(openness > 0.5), alpha=0.3, color='red', label='Open')
    ax8.set_xlabel('Time (s)')
    ax8.set_ylabel('Hand Openness (0=closed, 1=open)')
    ax8.set_title('Hand State')
    ax8.set_ylim([0, 1])
    ax8.grid(True, alpha=0.3)
    ax8.legend(fontsize=8)

    # 9. Detected Actions Timeline
    ax9 = fig.add_subplot(3, 3, 9)

    # Color map for actions
    action_colors = {
        'push': 'red',
        'pull': 'green',
        'lift': 'blue',
        'place': 'orange',
        'twist_open': 'purple',
        'twist_close': 'magenta',
        'pour': 'brown',
        'slide': 'cyan'
    }

    for i, action in enumerate(actions):
        action_type = action['action']
        color = action_colors.get(action_type, 'gray')
        ax9.barh(i, action['duration'], left=action['start_time'],
                height=0.8, color=color, alpha=0.7, edgecolor='black')

        # Add label
        label = action_type.upper().replace('_', ' ')
        if 'rotation_degrees' in action:
            label += f"\n{action['rotation_degrees']:.0f}°"

        ax9.text(action['start_time'] + action['duration']/2, i, label,
                ha='center', va='center', fontsize=8, fontweight='bold')

    ax9.set_xlabel('Time (s)')
    ax9.set_ylabel('Action #')
    ax9.set_title(f'Detected Actions ({len(actions)} total)')
    ax9.set_ylim([-0.5, len(actions) - 0.5])
    ax9.set_xlim([0, timestamps[-1]])
    ax9.grid(True, alpha=0.3, axis='x')
    ax9.set_yticks(range(len(actions)))
    ax9.set_yticklabels([f"#{i+1}" for i in range(len(actions))])

    # Add vertical lines for action boundaries
    for action in actions:
        ax9.axvline(x=action['start_time'], color='gray', linestyle='--', alpha=0.3, linewidth=0.5)
        ax9.axvline(x=action['end_time'], color='gray', linestyle='--', alpha=0.3, linewidth=0.5)

    plt.tight_layout()

    # Save figure
    output_file = Path(metric_file).stem + '_motion_visualization.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_file}")

    # Show statistics
    print("\n" + "="*70)
    print("MOTION STATISTICS")
    print("="*70)
    print()
    print(f"Duration: {timestamps[-1]:.2f} seconds")
    print(f"Frames: {len(timestamps)}")
    print()

    print("Position change:")
    print(f"  X (lateral):     {positions[-1, 0] - positions[0, 0]:+.3f}")
    print(f"  Y (vertical):    {positions[-1, 1] - positions[0, 1]:+.3f}")
    print(f"  Z (forward/back):{positions[-1, 2] - positions[0, 2]:+.3f}")
    print()

    print("Velocity analysis:")
    z_vels = velocities[:, 2]
    forward_frames = sum(1 for z in z_vels if z < -0.3)
    backward_frames = sum(1 for z in z_vels if z > 0.3)
    neutral_frames = len(z_vels) - forward_frames - backward_frames

    print(f"  Forward motion (PUSH):    {forward_frames} frames ({forward_frames/len(z_vels)*100:.1f}%)")
    print(f"  Backward motion (PULL):   {backward_frames} frames ({backward_frames/len(z_vels)*100:.1f}%)")
    print(f"  Neutral:                  {neutral_frames} frames ({neutral_frames/len(z_vels)*100:.1f}%)")
    print()

    print(f"Mean hand openness: {np.mean(openness):.2f}")
    print(f"  Closed frames (<0.3): {sum(1 for o in openness if o < 0.3)} ({sum(1 for o in openness if o < 0.3)/len(openness)*100:.1f}%)")
    print(f"  Open frames (>0.5):   {sum(1 for o in openness if o > 0.5)} ({sum(1 for o in openness if o > 0.5)/len(openness)*100:.1f}%)")
    print()

    print("Detected actions:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action['action'].upper()}: {action['start_time']:.2f}s - {action['end_time']:.2f}s ({action['duration']:.2f}s)")
        if 'rotation_degrees' in action:
            print(f"     Rotation: {action['rotation_degrees']:.1f}° {action['direction']}")

    print()
    print("="*70)
    print("INTERPRETATION")
    print("="*70)
    print()

    # Analyze dominant motion
    if backward_frames > forward_frames * 1.5:
        print("✅ PRIMARY MOTION: PULL (backward dominant)")
    elif forward_frames > backward_frames * 1.5:
        print("✅ PRIMARY MOTION: PUSH (forward dominant)")
    elif abs(forward_frames - backward_frames) < len(z_vels) * 0.1:
        print("⚠️  BIDIRECTIONAL: Equal forward and backward motion")
        print("   This suggests either:")
        print("   - Oscillating/jiggling motion")
        print("   - Back-and-forth movements")
        print("   - Camera/hand tremor")
    else:
        print("⚠️  COMPLEX MOTION: Mixed forward and backward")

    print()
    print(f"📊 Open the image file to see detailed visualization: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python visualize_motion_trajectory.py <metric_3d.json> <actions.json> <extraction_with_orientation.json>")
        sys.exit(1)

    metric_file = sys.argv[1]
    actions_file = sys.argv[2]
    extraction_file = sys.argv[3]

    print("🎨 Motion Trajectory Visualizer")
    print("="*70)

    visualize_motion(metric_file, actions_file, extraction_file)
