"""
ENHANCED ACTION DETECTION
Detect complex actions including:
- Container interactions (open/close door, drawer)
- Multi-stage actions (open → reach → grasp)
- Object state changes

Addresses Video #2 findings: missed "open refrigerator" action
"""

import json
import numpy as np
from pathlib import Path

class EnhancedActionDetector:
    """
    Detect complex manipulation actions including container interactions
    """

    def __init__(self):
        print("🔍 Enhanced Action Detector Initialized")

        # Action templates
        self.action_types = {
            'reach': 'Moving hand toward target',
            'grasp': 'Closing hand on object',
            'lift': 'Upward motion while grasping',
            'place': 'Downward motion then release',
            'pull': 'Backward motion with force',
            'push': 'Forward motion with force',
            'open': 'Pull motion on container (door/drawer)',
            'close': 'Push motion on container',
            'hold': 'Static grasp position',
            'release': 'Opening hand to drop object'
        }

    def detect_actions(self, metric_file, extraction_file):
        """
        Detect all actions including container interactions
        """
        print(f"\n{'='*70}")
        print(f"ENHANCED ACTION DETECTION")
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

        # Detect container objects
        containers = self._detect_containers(frames)

        # Detect container interactions
        container_actions = self._detect_container_interactions(
            positions, velocities, speeds, openness, timestamps, containers
        )

        # Detect manipulation actions
        manipulation_actions = self._detect_manipulation_actions(
            positions, velocities, speeds, openness, timestamps
        )

        # Combine and sequence actions
        all_actions = self._sequence_actions(container_actions, manipulation_actions)

        # Display results
        self._display_actions(all_actions, timestamps[-1])

        return all_actions

    def _detect_containers(self, frames):
        """
        Identify container objects (refrigerator, drawer, cabinet, door)
        """
        containers = []

        for frame_idx, frame in enumerate(frames):
            if not frame['objects'].get('detected'):
                continue

            objects = frame['objects'].get('objects', [])

            for obj in objects:
                obj_class = obj['class']

                # Container object classes
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

    def _detect_container_interactions(self, positions, velocities, speeds,
                                      openness, timestamps, containers):
        """
        Detect open/close actions on containers
        """
        actions = []

        if not containers:
            return actions

        # Check for pull/push patterns near containers
        i = 10
        while i < len(positions) - 10:
            # Look for pull motion (negative Z velocity = toward camera/person)
            z_vel = velocities[i, 2]
            speed = speeds[i]

            # Check if near container time
            container_nearby = any(
                abs(timestamps[i] - c['timestamp']) < 2.0
                for c in containers
            )

            if not container_nearby:
                i += 1
                continue

            # OPEN pattern: Pull motion (negative Z) with moderate speed
            if z_vel < -0.5 and speed > 1.0:
                # Check if sustained pull
                pull_duration = 0
                j = i
                while j < len(velocities) and velocities[j, 2] < -0.3:
                    pull_duration += 1/30.0  # Assuming 30fps
                    j += 1

                if pull_duration > 0.3:  # At least 0.3 seconds
                    # Find which container
                    closest_container = min(
                        [c for c in containers if abs(timestamps[i] - c['timestamp']) < 2.0],
                        key=lambda c: abs(timestamps[i] - c['timestamp']),
                        default=None
                    )

                    if closest_container:
                        actions.append({
                            'action': 'open',
                            'object': closest_container['type'],
                            'start_time': timestamps[i],
                            'end_time': timestamps[min(j, len(timestamps)-1)],
                            'duration': pull_duration,
                            'confidence': 0.8
                        })

                        # Skip ahead to avoid duplicate detection
                        i = j
                        continue

            # CLOSE pattern: Push motion (positive Z)
            elif z_vel > 0.5 and speed > 0.8:
                push_duration = 0
                j = i
                while j < len(velocities) and velocities[j, 2] > 0.3:
                    push_duration += 1/30.0
                    j += 1

                if push_duration > 0.2:
                    closest_container = min(
                        [c for c in containers if abs(timestamps[i] - c['timestamp']) < 2.0],
                        key=lambda c: abs(timestamps[i] - c['timestamp']),
                        default=None
                    )

                    if closest_container:
                        actions.append({
                            'action': 'close',
                            'object': closest_container['type'],
                            'start_time': timestamps[i],
                            'end_time': timestamps[min(j, len(timestamps)-1)],
                            'duration': push_duration,
                            'confidence': 0.75
                        })

                        # Skip ahead
                        i = j
                        continue

            # If no action detected, increment
            i += 1

        return actions

    def _detect_manipulation_actions(self, positions, velocities, speeds,
                                     openness, timestamps):
        """
        Detect basic manipulation: reach, grasp, lift, place
        """
        actions = []

        i = 0
        while i < len(speeds) - 10:  # Leave buffer for lookahead
            # REACH: Fast movement with hand open
            if speeds[i] > speeds.mean() + speeds.std() and openness[i] > 0.4:
                start = i
                while i < len(speeds) and speeds[i] > speeds.mean():
                    i += 1
                end = min(i, len(speeds) - 1)

                if end - start > 5:  # At least 5 frames
                    actions.append({
                        'action': 'reach',
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': timestamps[end] - timestamps[start],
                        'confidence': 0.75
                    })

            # GRASP: Hand closing significantly
            if i < len(openness) - 5:
                openness_change = openness[i+5] - openness[i]
                if openness_change < -0.15 and openness[i] > 0.3:
                    actions.append({
                        'action': 'grasp',
                        'object': 'unknown',
                        'start_time': timestamps[i],
                        'end_time': timestamps[i+5],
                        'duration': timestamps[i+5] - timestamps[i],
                        'confidence': 0.85
                    })
                    i += 5

            # LIFT: Upward motion (negative Y) while hand closed
            if i < len(velocities) and velocities[i, 1] < -0.5 and openness[i] < 0.3 and speeds[i] > 0.5:
                start = i
                while i < len(velocities) - 1 and velocities[i, 1] < -0.3:
                    i += 1
                end = min(i, len(velocities) - 1)

                if end - start > 5:
                    actions.append({
                        'action': 'lift',
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': timestamps[end] - timestamps[start],
                        'confidence': 0.8
                    })

            # PLACE: Downward motion (positive Y) then hand opens
            if i < len(velocities) and velocities[i, 1] > 0.5 and openness[i] < 0.3:
                start = i
                j = i
                while j < len(velocities) and velocities[j, 1] > 0.2:
                    j += 1

                # Check if hand opens after downward motion
                if j < len(openness) - 5:
                    if openness[j+5] - openness[j] > 0.1:
                        actions.append({
                            'action': 'place',
                            'object': 'unknown',
                            'start_time': timestamps[start],
                            'end_time': timestamps[j+5],
                            'duration': timestamps[j+5] - timestamps[start],
                            'confidence': 0.8
                        })
                        i = j + 5

            i += 1

        return actions

    def _sequence_actions(self, container_actions, manipulation_actions):
        """
        Combine and sequence all detected actions chronologically
        Then merge actions that are temporally close (slow movements)
        """
        all_actions = container_actions + manipulation_actions

        # Sort by start time
        all_actions.sort(key=lambda x: x['start_time'])

        # Merge temporally close actions of same type
        merged_actions = self._merge_slow_actions(all_actions)

        return merged_actions

    def _merge_slow_actions(self, actions):
        """
        Merge actions that are close in time (handles slow/interrupted movements)

        If same action type on same object within MERGE_WINDOW seconds,
        it's likely one slow action broken into pieces by velocity fluctuations.
        """
        if not actions:
            return actions

        MERGE_WINDOW = 3.0  # Merge actions within 3 seconds

        merged = []
        i = 0

        while i < len(actions):
            current = actions[i]

            # Look ahead for similar actions to merge
            j = i + 1
            while j < len(actions):
                next_action = actions[j]

                # Check if should merge
                same_type = current['action'] == next_action['action']
                same_object = current['object'] == next_action['object']
                close_in_time = (next_action['start_time'] - current['end_time']) < MERGE_WINDOW

                if same_type and same_object and close_in_time:
                    # Merge: extend current action to include next action
                    current['end_time'] = next_action['end_time']
                    current['duration'] = current['end_time'] - current['start_time']
                    j += 1  # Skip the merged action
                else:
                    break  # No more actions to merge

            merged.append(current)
            i = j  # Jump to next unmerged action

        return merged

    def _display_actions(self, actions, total_duration):
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
        print(f"ACTION SEQUENCE NARRATIVE")
        print(f"{'='*70}\n")

        narrative = self._create_narrative(actions)
        print(narrative)

    def _create_narrative(self, actions):
        """
        Create human-readable narrative of action sequence
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
            elif action_str == 'reach':
                narrative += f"{i}. {time_str}: Reached toward object\n"
            elif action_str == 'grasp':
                narrative += f"{i}. {time_str}: Grasped object\n"
            elif action_str == 'lift':
                narrative += f"{i}. {time_str}: Lifted object\n"
            elif action_str == 'place':
                narrative += f"{i}. {time_str}: Placed object down\n"

        return narrative


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python enhanced_action_detection.py <metric_3d.json> <extraction_with_colors.json>")
        return

    metric_file = sys.argv[1]
    extraction_file = sys.argv[2]

    detector = EnhancedActionDetector()
    actions = detector.detect_actions(metric_file, extraction_file)

    # Save results
    output_file = Path(metric_file).stem + '_enhanced_actions.json'
    with open(output_file, 'w') as f:
        json.dump({'actions': actions}, f, indent=2)

    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    main()
