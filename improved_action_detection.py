"""
IMPROVED ACTION DETECTION
Fixes duplicate action detection by using temporal clustering

Key improvements:
1. Detect container interaction PERIOD (start to end)
2. First pull = OPEN, last push = CLOSE
3. All middle motions = manipulation inside container
"""

import json
import numpy as np
from pathlib import Path

class ImprovedActionDetector:
    """
    Detect actions with temporal awareness to avoid duplicates
    """

    def __init__(self):
        print("🔍 Improved Action Detector (Temporal Clustering)")

    def detect_actions(self, metric_file, extraction_file):
        """
        Detect actions using temporal clustering approach
        """
        print(f"\n{'='*70}")
        print(f"IMPROVED ACTION DETECTION")
        print(f"{'='*70}\n")

        # Load data
        print(f"📂 Loading data...")
        with open(metric_file, 'r') as f:
            metric_data = json.load(f)

        with open(extraction_file, 'r') as f:
            extraction_data = json.load(f)

        timesteps = metric_data['timesteps']
        frames = extraction_data['frames']

        # Extract trajectories
        positions = np.array([ts['observations']['end_effector_pos_metric'] for ts in timesteps])
        velocities = np.array([ts['kinematics']['velocity'] for ts in timesteps])
        speeds = np.array([ts['kinematics']['speed'] for ts in timesteps])
        openness = np.array([ts['observations']['gripper_openness'] for ts in timesteps])
        timestamps = np.array([ts['timestamp'] for ts in timesteps])

        # Detect containers
        containers = self._detect_containers(frames)

        if not containers:
            print("⚠️  No containers detected, using general action detection")
            actions = self._detect_general_actions(positions, velocities, speeds, openness, timestamps)
        else:
            # NEW: Detect container interaction PERIOD
            interaction_period = self._detect_interaction_period(
                containers, timestamps, velocities, speeds
            )

            if interaction_period:
                print(f"\n🎯 CONTAINER INTERACTION DETECTED:")
                print(f"   Container: {interaction_period['container_type']}")
                print(f"   Start: {interaction_period['start_time']:.1f}s")
                print(f"   End: {interaction_period['end_time']:.1f}s")
                print(f"   Duration: {interaction_period['duration']:.1f}s\n")

                # Detect actions within this period
                actions = self._detect_container_period_actions(
                    interaction_period, positions, velocities, speeds, openness, timestamps
                )
            else:
                print("⚠️  No clear container interaction period found")
                actions = self._detect_general_actions(positions, velocities, speeds, openness, timestamps)

        # Display results
        self._display_actions(actions)

        return actions

    def _detect_containers(self, frames):
        """
        Identify container objects
        """
        containers = []

        for frame_idx, frame in enumerate(frames):
            if not frame['objects'].get('detected'):
                continue

            objects = frame['objects'].get('objects', [])

            for obj in objects:
                obj_class = obj['class']

                if obj_class in ['refrigerator', 'oven', 'microwave', 'door']:
                    containers.append({
                        'type': obj_class,
                        'frame': frame_idx,
                        'bbox': obj['bbox'],
                        'timestamp': frame['timestamp']
                    })

        # Count occurrences
        container_types = {}
        for c in containers:
            ctype = c['type']
            container_types[ctype] = container_types.get(ctype, 0) + 1

        print(f"\n📦 CONTAINERS DETECTED:")
        for ctype, count in container_types.items():
            print(f"   • {ctype}: {count} frames")

        return containers

    def _detect_interaction_period(self, containers, timestamps, velocities, speeds):
        """
        Detect the PERIOD during which user is interacting with container

        Strategy:
        1. Container visible in frames → user is near it
        2. Find continuous period with high activity near container
        3. First significant pull = open
        4. Last significant push = close
        """
        if not containers:
            return None

        # Get container visibility timeline
        container_type = containers[0]['type']
        container_times = [c['timestamp'] for c in containers]

        start_time = min(container_times)
        end_time = max(container_times)

        # Find indices for this time range
        start_idx = np.argmin(np.abs(timestamps - start_time))
        end_idx = np.argmin(np.abs(timestamps - end_time))

        return {
            'container_type': container_type,
            'start_time': timestamps[start_idx],
            'end_time': timestamps[end_idx],
            'duration': timestamps[end_idx] - timestamps[start_idx],
            'start_idx': start_idx,
            'end_idx': end_idx
        }

    def _detect_container_period_actions(self, period, positions, velocities,
                                         speeds, openness, timestamps):
        """
        Detect actions within the container interaction period

        Key insight:
        - FIRST pull motion = OPEN
        - LAST push motion = CLOSE
        - Middle motions = manipulation inside
        """
        actions = []

        start_idx = period['start_idx']
        end_idx = period['end_idx']
        container = period['container_type']

        # Get Z velocities in this period
        z_vels = velocities[start_idx:end_idx+1, 2]
        period_speeds = speeds[start_idx:end_idx+1]
        period_times = timestamps[start_idx:end_idx+1]

        # OPEN: Find FIRST sustained pull
        open_action = self._find_first_pull(
            z_vels, period_speeds, period_times, container
        )
        if open_action:
            actions.append(open_action)

        # CLOSE: Find LAST sustained push
        close_action = self._find_last_push(
            z_vels, period_speeds, period_times, container
        )
        if close_action:
            actions.append(close_action)

        # MANIPULATION: Detect grasp/lift between open and close
        manip_start = open_action['end_time'] if open_action else period['start_time']
        manip_end = close_action['start_time'] if close_action else period['end_time']

        manip_actions = self._detect_manipulation_in_range(
            positions, velocities, speeds, openness, timestamps,
            manip_start, manip_end
        )
        actions.extend(manip_actions)

        return actions

    def _find_first_pull(self, z_vels, speeds, times, container):
        """
        Find the FIRST sustained pull motion (door opening)
        """
        PULL_THRESHOLD = -0.5
        SPEED_THRESHOLD = 1.0
        MIN_DURATION = 0.2

        for i in range(len(z_vels) - 5):
            if z_vels[i] < PULL_THRESHOLD and speeds[i] > SPEED_THRESHOLD:
                # Check if sustained
                duration = 0
                j = i
                while j < len(z_vels) and z_vels[j] < -0.3:
                    duration += 1/30.0
                    j += 1

                if duration > MIN_DURATION:
                    return {
                        'action': 'open',
                        'object': container,
                        'start_time': times[i],
                        'end_time': times[min(j, len(times)-1)],
                        'duration': duration,
                        'confidence': 0.9
                    }

        return None

    def _find_last_push(self, z_vels, speeds, times, container):
        """
        Find the LAST sustained push motion (door closing)
        """
        PUSH_THRESHOLD = 0.5
        SPEED_THRESHOLD = 0.8
        MIN_DURATION = 0.15

        # Search backwards
        for i in range(len(z_vels) - 1, 5, -1):
            if z_vels[i] > PUSH_THRESHOLD and speeds[i] > SPEED_THRESHOLD:
                # Check if sustained (going backwards)
                duration = 0
                j = i
                while j >= 0 and z_vels[j] > 0.3:
                    duration += 1/30.0
                    j -= 1

                if duration > MIN_DURATION:
                    return {
                        'action': 'close',
                        'object': container,
                        'start_time': times[max(j, 0)],
                        'end_time': times[i],
                        'duration': duration,
                        'confidence': 0.85
                    }

        return None

    def _detect_manipulation_in_range(self, positions, velocities, speeds,
                                      openness, timestamps, start_time, end_time):
        """
        Detect manipulation actions (grasp, lift) in a time range
        """
        actions = []

        # Find indices for this time range
        start_idx = np.argmin(np.abs(timestamps - start_time))
        end_idx = np.argmin(np.abs(timestamps - end_time))

        # Look for LIFT actions (negative Y velocity while hand closed)
        i = start_idx
        while i < end_idx - 5:
            if velocities[i, 1] < -0.5 and openness[i] < 0.3 and speeds[i] > 0.5:
                start = i
                while i < end_idx and velocities[i, 1] < -0.3:
                    i += 1
                end = min(i, end_idx)

                if end - start > 5:  # At least 5 frames
                    actions.append({
                        'action': 'lift',
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': timestamps[end] - timestamps[start],
                        'confidence': 0.8
                    })
                    continue  # Skip ahead

            i += 1

        # Merge close lifts (item slipped, picked up again)
        # Use longer window to merge all manipulation within container
        actions = self._merge_close_actions(actions, merge_window=5.0)

        return actions

    def _merge_close_actions(self, actions, merge_window=2.0):
        """
        Merge actions of same type that are close in time
        """
        if not actions:
            return actions

        merged = []
        i = 0

        while i < len(actions):
            current = actions[i]

            # Look ahead for similar actions
            j = i + 1
            while j < len(actions):
                next_action = actions[j]

                same_type = current['action'] == next_action['action']
                close_in_time = (next_action['start_time'] - current['end_time']) < merge_window

                if same_type and close_in_time:
                    # Merge
                    current['end_time'] = next_action['end_time']
                    current['duration'] = current['end_time'] - current['start_time']
                    j += 1
                else:
                    break

            merged.append(current)
            i = j

        return merged

    def _detect_general_actions(self, positions, velocities, speeds, openness, timestamps):
        """
        Fallback: detect general manipulation actions without container context
        """
        actions = []

        # Simple reach/grasp/lift detection
        i = 0
        while i < len(speeds) - 10:
            # LIFT: Upward motion while hand closed
            if velocities[i, 1] < -0.5 and openness[i] < 0.3 and speeds[i] > 0.5:
                start = i
                while i < len(velocities) and velocities[i, 1] < -0.3:
                    i += 1
                end = min(i, len(velocities) - 1)

                if end - start > 5:
                    actions.append({
                        'action': 'lift',
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': timestamps[end] - timestamps[start],
                        'confidence': 0.75
                    })
                    continue

            i += 1

        return actions

    def _display_actions(self, actions):
        """
        Display detected actions
        """
        print(f"\n{'='*70}")
        print(f"DETECTED ACTIONS ({len(actions)} total)")
        print(f"{'='*70}\n")

        if not actions:
            print("   No clear actions detected")
            return

        for i, action in enumerate(actions, 1):
            print(f"{i}. {action['action'].upper()}")
            print(f"   Object: {action['object']}")
            print(f"   Time: {action['start_time']:.1f}s - {action['end_time']:.1f}s")
            print(f"   Duration: {action['duration']:.2f}s")
            print(f"   Confidence: {action['confidence']:.0%}\n")

        # Create narrative
        print(f"{'='*70}")
        print(f"ACTION NARRATIVE")
        print(f"{'='*70}\n")

        narrative = self._create_narrative(actions)
        print(narrative)

    def _create_narrative(self, actions):
        """
        Create human-readable narrative
        """
        if not actions:
            return "No significant actions detected."

        narrative = "Based on the detected actions, here's what happened:\n\n"

        for i, action in enumerate(actions, 1):
            time_str = f"At t={action['start_time']:.1f}s"
            action_str = action['action']
            object_str = action['object']

            if action_str == 'open':
                narrative += f"{i}. {time_str}: Opened the {object_str}\n"
            elif action_str == 'close':
                narrative += f"{i}. {time_str}: Closed the {object_str}\n"
            elif action_str == 'lift':
                narrative += f"{i}. {time_str}: Lifted object (duration: {action['duration']:.1f}s)\n"

        return narrative


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python improved_action_detection.py <metric_3d.json> <extraction_with_colors.json>")
        return

    metric_file = sys.argv[1]
    extraction_file = sys.argv[2]

    detector = ImprovedActionDetector()
    actions = detector.detect_actions(metric_file, extraction_file)

    # Save results
    output_file = Path(metric_file).stem + '_improved_actions.json'
    with open(output_file, 'w') as f:
        json.dump({'actions': actions}, f, indent=2)

    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    main()
