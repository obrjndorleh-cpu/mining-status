"""
ADVANCED ACTION DETECTION
Detects manipulation primitives including rotation-based actions

New capabilities:
- Twist/rotation (bottle opening/closing)
- Pouring (sustained tilted pose)
- Placement (downward + release)
- Plus all previous: open/close container, lift, reach, grasp
"""

import json
import numpy as np
from pathlib import Path


class AdvancedActionDetector:
    """
    Detect all manipulation actions including rotation-based
    """

    def __init__(self):
        print("🔍 Advanced Action Detector (with Rotation)")

    def detect_actions(self, metric_file, extraction_file):
        """
        Detect all actions using position + orientation
        """
        print(f"\n{'='*70}")
        print(f"ADVANCED ACTION DETECTION")
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

        # Extract orientations
        orientations = self._extract_orientations(frames)

        # Detect containers
        containers = self._detect_containers(frames)

        # Detect all action types
        all_actions = []

        # Container interactions
        if containers:
            container_actions = self._detect_container_interactions(
                positions, velocities, speeds, openness, timestamps, containers
            )
            all_actions.extend(container_actions)

        # Rotation-based actions (twist, pour)
        rotation_actions = self._detect_rotation_actions(
            positions, velocities, speeds, openness, timestamps, orientations, frames
        )
        all_actions.extend(rotation_actions)

        # Linear manipulation actions
        manipulation_actions = self._detect_linear_manipulation(
            positions, velocities, speeds, openness, timestamps
        )
        all_actions.extend(manipulation_actions)

        # Sort by time
        all_actions.sort(key=lambda x: x['start_time'])

        # Merge temporally close actions of same type
        all_actions = self._merge_close_actions(all_actions)

        # Filter to keep only primary twist actions (first open, last close)
        all_actions = self._filter_primary_twists(all_actions)

        # Display results
        self._display_actions(all_actions, timestamps[-1])

        return all_actions

    def _extract_orientations(self, frames):
        """
        Extract orientation data from frames
        """
        orientations = []

        for frame in frames:
            if not frame['hands']['detected']:
                orientations.append(None)
                continue

            hands = frame['hands'].get('hands', [])
            if not hands or 'orientation' not in hands[0]:
                orientations.append(None)
                continue

            orient = hands[0]['orientation']
            orientations.append({
                'roll': orient['roll'],
                'pitch': orient['pitch'],
                'yaw': orient['yaw'],
                'palm_normal': np.array(orient['palm_normal'])
            })

        return orientations

    def _detect_rotation_actions(self, positions, velocities, speeds,
                                 openness, timestamps, orientations, frames):
        """
        Detect twist and pour actions using hand rotation
        """
        actions = []

        if not any(orientations):
            print("⚠️  No orientation data available")
            return actions

        # Compute rotation rates
        roll_angles = []
        pitch_angles = []
        valid_indices = []

        for i, orient in enumerate(orientations):
            if orient:
                roll_angles.append(orient['roll'])
                pitch_angles.append(orient['pitch'])
                valid_indices.append(i)

        if len(roll_angles) < 10:
            return actions

        roll_angles = np.array(roll_angles)
        pitch_angles = np.array(pitch_angles)

        # Unwrap angles (handle -180/+180 wraparound)
        roll_angles = np.unwrap(np.radians(roll_angles))
        pitch_angles = np.unwrap(np.radians(pitch_angles))

        # Compute rotation rates
        roll_rate = np.gradient(roll_angles, timestamps[valid_indices])
        pitch_rate = np.gradient(pitch_angles, timestamps[valid_indices])

        # TWIST DETECTION: High roll rate while grasping AND stationary
        twist_actions = self._detect_twist(
            roll_angles, roll_rate, openness[valid_indices],
            timestamps[valid_indices], positions[valid_indices], frames, valid_indices
        )
        actions.extend(twist_actions)

        # POUR DETECTION: Sustained pitch tilt
        pour_actions = self._detect_pour(
            pitch_angles, pitch_rate, positions[valid_indices],
            timestamps[valid_indices], frames, valid_indices
        )
        actions.extend(pour_actions)

        return actions

    def _detect_twist(self, roll_angles, roll_rate, openness, timestamps, positions, frames, valid_indices):
        """
        Detect twisting motion (bottle opening/closing)

        Key distinction: Twist requires rotation while hand is STATIONARY
        (rotating bottle cap in place, not rotating hand while moving object)
        """
        actions = []

        # Thresholds
        TWIST_RATE_THRESHOLD = 2.0  # radians/second
        MIN_TWIST_DURATION = 0.3  # seconds (increased from 0.2)
        MIN_ROTATION = np.radians(40)  # At least 40 degrees (increased from 30)
        MAX_HAND_MOVEMENT = 0.3  # Hand must stay relatively stationary (meters)

        i = 0
        while i < len(roll_rate) - 10:
            # High rotation rate while hand closed
            if abs(roll_rate[i]) > TWIST_RATE_THRESHOLD and openness[i] < 0.3:
                start = i
                start_angle = roll_angles[i]
                start_pos = positions[i]

                # Track twist direction
                direction = 'clockwise' if roll_rate[i] > 0 else 'counter-clockwise'

                # Follow the twist
                j = i
                while j < len(roll_rate) and abs(roll_rate[j]) > TWIST_RATE_THRESHOLD * 0.5:
                    j += 1

                end = min(j, len(roll_rate) - 1)
                end_angle = roll_angles[end]
                end_pos = positions[end]
                duration = timestamps[end] - timestamps[start]
                rotation_amount = abs(end_angle - start_angle)

                # Check hand movement during rotation
                hand_movement = np.linalg.norm(end_pos - start_pos)

                # Only count as twist if hand stayed relatively stationary
                if (duration > MIN_TWIST_DURATION and
                    rotation_amount > MIN_ROTATION and
                    hand_movement < MAX_HAND_MOVEMENT):
                    # Determine if opening or closing based on context
                    global_frame_idx = valid_indices[start]
                    obj = self._get_object_near_hand(frames[global_frame_idx])

                    # Heuristic: counter-clockwise = opening, clockwise = closing (for bottles)
                    if direction == 'counter-clockwise':
                        action_type = 'twist_open'
                    else:
                        action_type = 'twist_close'

                    actions.append({
                        'action': action_type,
                        'object': obj if obj else 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': duration,
                        'rotation_degrees': float(np.degrees(rotation_amount)),
                        'direction': direction,
                        'confidence': 0.85
                    })

                    i = j
                    continue

            i += 1

        return actions

    def _detect_pour(self, pitch_angles, pitch_rate, positions, timestamps, frames, valid_indices):
        """
        Detect pouring action (sustained tilted pose)
        """
        actions = []

        # Thresholds
        POUR_PITCH_THRESHOLD = np.radians(30)  # At least 30 degrees tilt
        MIN_POUR_DURATION = 0.5  # At least 0.5 seconds
        MAX_MOTION_SPEED = 0.5  # Hand mostly stationary

        i = 0
        while i < len(pitch_angles) - 15:  # Need at least 15 frames
            pitch = pitch_angles[i]

            # Hand tilted significantly
            if pitch < -POUR_PITCH_THRESHOLD:  # Negative = tilted down for pouring
                start = i

                # Check if sustained
                j = i
                while j < len(pitch_angles) and pitch_angles[j] < -POUR_PITCH_THRESHOLD * 0.7:
                    j += 1

                end = min(j, len(pitch_angles) - 1)
                duration = timestamps[end] - timestamps[start]

                # Check if hand is relatively stationary (pouring, not moving)
                if end > start + 1:
                    motion_during = np.linalg.norm(positions[end] - positions[start]) / duration

                    if duration > MIN_POUR_DURATION and motion_during < MAX_MOTION_SPEED:
                        global_frame_idx = valid_indices[start]
                        source_obj = self._get_object_near_hand(frames[global_frame_idx])

                        actions.append({
                            'action': 'pour',
                            'object': source_obj if source_obj else 'unknown',
                            'start_time': timestamps[start],
                            'end_time': timestamps[end],
                            'duration': duration,
                            'tilt_degrees': float(np.degrees(abs(pitch_angles[start]))),
                            'confidence': 0.8
                        })

                        i = j
                        continue

            i += 1

        return actions

    def _get_object_near_hand(self, frame):
        """
        Get object that hand is likely interacting with
        """
        if not frame['objects']['detected']:
            return None

        objects = frame['objects'].get('objects', [])

        # Prioritize bottles and cups for twist/pour
        for obj in objects:
            if obj['class'] in ['bottle', 'cup', 'wine glass']:
                return obj['class']

        # Return first object
        if objects:
            return objects[0]['class']

        return None

    def _detect_linear_manipulation(self, positions, velocities, speeds, openness, timestamps):
        """
        Detect manipulation actions: lift, place, push, pull, slide
        """
        actions = []

        i = 0
        while i < len(speeds) - 10:
            # PUSH/PULL: Depth motion (Z-axis) with hand contact
            # KEY: Use NET DISPLACEMENT to determine direction (velocity can be noisy)
            z_vel = velocities[i, 2] if len(velocities[i]) > 2 else 0
            y_vel = velocities[i, 1]

            # Detect significant depth motion (forward OR backward)
            if abs(z_vel) > 0.5 and abs(y_vel) < 0.5 and speeds[i] > 0.5:
                start = i
                j = i

                # Track sustained motion period
                while j < len(velocities) - 1 and j < start + 90:  # Look ahead up to 3 seconds
                    z_check = velocities[j, 2] if len(velocities[j]) > 2 else 0

                    # Stop if motion stops for too long
                    if abs(z_check) < 0.2 and speeds[j] < 0.3:
                        # Check if motion stopped for 30 frames
                        stopped_count = 0
                        for k in range(j, min(j+30, len(velocities))):
                            if abs(velocities[k, 2]) < 0.2 and speeds[k] < 0.3:
                                stopped_count += 1
                        if stopped_count > 20:
                            break

                    j += 1

                end = min(j, len(velocities) - 1)
                duration = timestamps[end] - timestamps[start]

                # KEY: Use NET DISPLACEMENT to determine if PUSH or PULL
                # This works with boundary detection to get correct direction
                net_z_displacement = positions[end, 2] - positions[start, 2]

                if duration > 0.5 and abs(net_z_displacement) > 0.1:
                    # Determine action by NET displacement (not velocity)
                    if net_z_displacement < 0:
                        # Negative Z = Forward = PUSH
                        action_type = 'push'
                    else:
                        # Positive Z = Backward = PULL
                        action_type = 'pull'

                    actions.append({
                        'action': action_type,
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': duration,
                        'confidence': 0.75,
                        'net_displacement': float(net_z_displacement)
                    })
                    i = j
                    continue

            # SLIDE: Lateral motion (X-velocity dominant) with minimal vertical change
            x_vel = velocities[i, 0]

            if abs(x_vel) > 0.4 and abs(y_vel) < 0.3 and abs(z_vel) < 0.4:  # Primarily sideways
                start = i
                j = i

                # Track sustained lateral motion
                while j < len(velocities) and abs(velocities[j, 0]) > 0.2:
                    j += 1

                end = min(j, len(velocities) - 1)
                duration = timestamps[end] - timestamps[start]

                if duration > 0.3 and end - start > 5:
                    actions.append({
                        'action': 'slide',
                        'object': 'unknown',
                        'start_time': timestamps[start],
                        'end_time': timestamps[end],
                        'duration': duration,
                        'confidence': 0.7
                    })
                    i = j
                    continue

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

            # PLACE: Downward motion then hand opens (relaxed for gentle placement)
            # IMPORTANT: Only trigger if NOT also pushing (to avoid false positives)
            if velocities[i, 1] > 0.3 and openness[i] < 0.5:  # Relaxed thresholds
                # Check that Z-velocity is NOT strongly negative (not pushing)
                z_vel_check = velocities[i, 2] if len(velocities[i]) > 2 else 0

                if abs(z_vel_check) < 0.4:  # Not pushing forward
                    start = i
                    j = i
                    while j < len(velocities) and velocities[j, 1] > 0.15:  # Gentler downward motion
                        j += 1

                    # Check if hand opens after downward motion
                    if j < len(openness) - 10:  # Look further ahead
                        # Check for opening in next 10 frames
                        max_opening = max(openness[j:j+10]) if j+10 < len(openness) else max(openness[j:])
                        if max_opening - openness[j] > 0.05:  # Any opening detected
                            actions.append({
                                'action': 'place',
                                'object': 'unknown',
                                'start_time': timestamps[start],
                                'end_time': timestamps[min(j+10, len(timestamps)-1)],
                                'duration': timestamps[min(j+10, len(timestamps)-1)] - timestamps[start],
                                'confidence': 0.7
                            })
                            i = j + 10
                            continue

            i += 1

        return actions

    def _detect_containers(self, frames):
        """
        Identify container objects with robust filtering

        Requirements to avoid false positives:
        1. Container must be visible in multiple consecutive frames
        2. Minimum confidence threshold
        3. Minimum percentage of video duration
        """
        containers = []
        MIN_CONTAINER_CONFIDENCE = 0.5  # YOLOv8 confidence threshold
        MIN_CONTAINER_FRAMES = 20  # Must appear in at least 20 frames (~0.67s)
        MIN_PERCENTAGE = 0.10  # Must be visible for at least 10% of video

        # First pass: collect all container detections
        container_detections = {}  # {container_type: [(frame_idx, timestamp, bbox)]}

        for frame_idx, frame in enumerate(frames):
            if not frame['objects'].get('detected'):
                continue

            objects = frame['objects'].get('objects', [])

            for obj in objects:
                obj_class = obj['class']
                obj_conf = obj.get('confidence', 1.0)  # Default to 1.0 if not present

                if obj_class in ['refrigerator', 'oven', 'microwave', 'door']:
                    # Check confidence threshold
                    if obj_conf >= MIN_CONTAINER_CONFIDENCE:
                        if obj_class not in container_detections:
                            container_detections[obj_class] = []

                        container_detections[obj_class].append({
                            'frame': frame_idx,
                            'timestamp': frame['timestamp'],
                            'bbox': obj['bbox'],
                            'confidence': obj_conf
                        })

        # Second pass: filter out sporadic detections
        total_frames = len(frames)

        for container_type, detections in container_detections.items():
            num_detections = len(detections)
            percentage = num_detections / total_frames

            # Check if container is significantly present
            if num_detections >= MIN_CONTAINER_FRAMES and percentage >= MIN_PERCENTAGE:
                # Check for temporal continuity (not just sporadic detections)
                frame_indices = [d['frame'] for d in detections]
                frame_gaps = [frame_indices[i+1] - frame_indices[i] for i in range(len(frame_indices)-1)]
                avg_gap = sum(frame_gaps) / len(frame_gaps) if frame_gaps else 0

                # If average gap is small (<10 frames), it's likely a real container
                if avg_gap < 10:
                    # Add all detections for this valid container
                    for det in detections:
                        containers.append({
                            'type': container_type,
                            'frame': det['frame'],
                            'bbox': det['bbox'],
                            'timestamp': det['timestamp']
                        })

                    print(f"   ✅ Valid container: {container_type} ({num_detections} frames, {percentage*100:.1f}%, avg gap {avg_gap:.1f})")
                else:
                    print(f"   ⚠️ Filtered out: {container_type} (sporadic detections, avg gap {avg_gap:.1f} frames)")
            else:
                print(f"   ⚠️ Filtered out: {container_type} (only {num_detections} frames, {percentage*100:.1f}%)")

        return containers

    def _detect_container_interactions(self, positions, velocities, speeds,
                                       openness, timestamps, containers):
        """
        Detect open/close on containers (from improved_action_detection.py)
        """
        actions = []

        if not containers:
            return actions

        # Get interaction period
        container_times = [c['timestamp'] for c in containers]
        start_time = min(container_times)
        end_time = max(container_times)

        start_idx = np.argmin(np.abs(timestamps - start_time))
        end_idx = np.argmin(np.abs(timestamps - end_time))

        z_vels = velocities[start_idx:end_idx+1, 2]
        period_speeds = speeds[start_idx:end_idx+1]
        period_times = timestamps[start_idx:end_idx+1]

        container_type = containers[0]['type']

        # Find FIRST pull (open)
        for i in range(len(z_vels) - 5):
            if z_vels[i] < -0.5 and period_speeds[i] > 1.0:
                duration = 0
                j = i
                while j < len(z_vels) and z_vels[j] < -0.3:
                    duration += 1/30.0
                    j += 1

                if duration > 0.2:
                    actions.append({
                        'action': 'open',
                        'object': container_type,
                        'start_time': period_times[i],
                        'end_time': period_times[min(j, len(period_times)-1)],
                        'duration': duration,
                        'confidence': 0.9
                    })
                    break

        # Find LAST push (close)
        for i in range(len(z_vels) - 1, 5, -1):
            if z_vels[i] > 0.5 and period_speeds[i] > 0.8:
                duration = 0
                j = i
                while j >= 0 and z_vels[j] > 0.3:
                    duration += 1/30.0
                    j -= 1

                if duration > 0.15:
                    actions.append({
                        'action': 'close',
                        'object': container_type,
                        'start_time': period_times[max(j, 0)],
                        'end_time': period_times[i],
                        'duration': duration,
                        'confidence': 0.85
                    })
                    break

        return actions

    def _filter_primary_twists(self, actions):
        """
        Filter twist actions to keep only primary ones
        Strategy: Keep FIRST twist_open and LAST twist_close
        (Intermediate twists are likely grip adjustments, not actual open/close)
        """
        twist_opens = [a for a in actions if a['action'] == 'twist_open']
        twist_closes = [a for a in actions if a['action'] == 'twist_close']
        other_actions = [a for a in actions if a['action'] not in ['twist_open', 'twist_close']]

        filtered = []

        # Keep first significant twist_open (biggest rotation or first one)
        if twist_opens:
            # Find most significant open (largest rotation)
            significant_open = max(twist_opens, key=lambda x: x['rotation_degrees'])
            # But if first open is also significant (>30°), prefer it
            if twist_opens[0]['rotation_degrees'] > 30:
                significant_open = twist_opens[0]
            filtered.append(significant_open)

        # Keep last significant twist_close
        if twist_closes:
            # Find most significant close (largest rotation)
            significant_close = max(twist_closes, key=lambda x: x['rotation_degrees'])
            # But if last close is also significant (>30°), prefer it
            if twist_closes[-1]['rotation_degrees'] > 30:
                significant_close = twist_closes[-1]
            filtered.append(significant_close)

        # Keep all other actions
        filtered.extend(other_actions)

        # Re-sort by time
        filtered.sort(key=lambda x: x['start_time'])

        return filtered

    def _merge_close_actions(self, actions):
        """
        Merge actions of same type that are close in time
        Handles slow/interrupted motions (twist bottle slowly, etc.)
        """
        if not actions:
            return actions

        MERGE_WINDOWS = {
            'twist_open': 3.0,    # Merge twists within 3 seconds
            'twist_close': 3.0,
            'pour': 2.0,          # Merge pours within 2 seconds
            'lift': 5.0,
            'place': 2.0,
            'open': 5.0,          # Container actions
            'close': 5.0
        }

        merged = []
        i = 0

        while i < len(actions):
            current = actions[i]
            action_type = current['action']
            merge_window = MERGE_WINDOWS.get(action_type, 3.0)

            # Look ahead for similar actions to merge
            j = i + 1
            while j < len(actions):
                next_action = actions[j]

                same_type = current['action'] == next_action['action']
                close_in_time = (next_action['start_time'] - current['end_time']) < merge_window

                if same_type and close_in_time:
                    # Merge: extend current action to include next action
                    current['end_time'] = next_action['end_time']
                    current['duration'] = current['end_time'] - current['start_time']

                    # For rotation actions, accumulate rotation
                    if 'rotation_degrees' in current and 'rotation_degrees' in next_action:
                        current['rotation_degrees'] += next_action['rotation_degrees']

                    j += 1
                else:
                    break

            merged.append(current)
            i = j

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
            print(f"{i}. {action['action'].upper().replace('_', ' ')}")
            print(f"   Object: {action['object']}")
            print(f"   Time: {action['start_time']:.1f}s - {action['end_time']:.1f}s")
            print(f"   Duration: {action['duration']:.2f}s")

            # Extra info for specific actions
            if 'rotation_degrees' in action:
                print(f"   Rotation: {action['rotation_degrees']:.1f}° ({action['direction']})")
            if 'tilt_degrees' in action:
                print(f"   Tilt: {action['tilt_degrees']:.1f}°")

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

            if action_str == 'twist_open':
                narrative += f"{i}. {time_str}: Twisted {object_str} to open it ({action['rotation_degrees']:.0f}° {action['direction']})\n"
            elif action_str == 'twist_close':
                narrative += f"{i}. {time_str}: Twisted {object_str} to close it ({action['rotation_degrees']:.0f}° {action['direction']})\n"
            elif action_str == 'pour':
                narrative += f"{i}. {time_str}: Poured from {object_str} (tilted {action['tilt_degrees']:.0f}° for {action['duration']:.1f}s)\n"
            elif action_str == 'open':
                narrative += f"{i}. {time_str}: Opened the {object_str}\n"
            elif action_str == 'close':
                narrative += f"{i}. {time_str}: Closed the {object_str}\n"
            elif action_str == 'lift':
                narrative += f"{i}. {time_str}: Lifted object\n"
            elif action_str == 'place':
                narrative += f"{i}. {time_str}: Placed object down\n"

        return narrative


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python advanced_action_detection.py <metric_3d.json> <extraction_with_orientation.json>")
        return

    metric_file = sys.argv[1]
    extraction_file = sys.argv[2]

    detector = AdvancedActionDetector()
    actions = detector.detect_actions(metric_file, extraction_file)

    # Save results
    output_file = Path(metric_file).stem + '_advanced_actions.json'
    with open(output_file, 'w') as f:
        json.dump({'actions': actions}, f, indent=2)

    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    main()
