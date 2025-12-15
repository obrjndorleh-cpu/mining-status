"""
CONTACT-BASED ACTION DETECTION (Deterministic, Physics-Based)

Philosophy: Actions are defined by:
1. Which fingers are in contact with object
2. Object type/properties
3. Motion pattern (small/large, circular/linear)
4. Surface contact (is object touching surface?)

NO NEURAL NETWORKS - Pure biomechanics + context
"""

import numpy as np

class ContactBasedActionDetector:
    """
    Detect actions from hand-object contact patterns + physics
    """

    # Finger configurations for different grips
    GRIPS = {
        'precision_pinch': {
            'fingers': ['thumb', 'index'],
            'distance': 0.02,  # meters between thumb and index
            'description': 'Thumb + index finger pinched together'
        },
        'power_grasp': {
            'fingers': ['thumb', 'index', 'middle', 'ring', 'pinky'],
            'openness': 0.2,
            'description': 'Full hand wrapped around object'
        },
        'tripod_grip': {
            'fingers': ['thumb', 'index', 'middle'],
            'distance': 0.03,
            'description': 'Three-finger grip (pen, chopsticks)'
        }
    }

    # Action signatures (deterministic rules)
    ACTION_SIGNATURES = {
        'writing': {
            'grip': 'tripod_grip',
            'object_types': ['pen', 'pencil', 'marker'],
            'motion': {
                'type': 'small_circular',
                'amplitude': 0.05,  # <5cm movements
                'frequency': 1.0,   # ~1 Hz
            },
            'surface_contact': True,
            'description': 'Pen in tripod grip, small motions on surface'
        },

        'pointing': {
            'grip': None,  # No grip, extended finger
            'finger_extended': 'index',
            'motion': {
                'type': 'directional',
                'speed': 0.3  # Moderate speed
            },
            'description': 'Index finger extended, directional motion'
        },

        'cutting': {
            'grip': 'power_grasp',
            'object_types': ['knife'],
            'motion': {
                'type': 'sawing',
                'direction': 'horizontal',
                'repetitive': True
            },
            'surface_contact': True,
            'description': 'Knife in power grip, sawing motion on surface'
        },

        'stirring': {
            'grip': 'power_grasp',
            'object_types': ['spoon', 'spatula'],
            'motion': {
                'type': 'circular',
                'plane': 'horizontal',
                'radius': 0.1,  # ~10cm circles
                'continuous': True
            },
            'description': 'Spoon/spatula in circular motion'
        },

        'typing': {
            'grip': None,
            'finger_pattern': 'sequential_taps',
            'motion': {
                'type': 'discrete_taps',
                'amplitude': 0.02,  # Small vertical motions
                'frequency': 3.0    # ~3 Hz (fast typing)
            },
            'surface_contact': True,
            'description': 'Fingers tapping surface sequentially'
        }
    }

    def detect_grip(self, hand_landmarks, gripper_openness):
        """
        Deterministically detect grip type from hand pose

        Args:
            hand_landmarks: Dict of finger positions
            gripper_openness: 0-1 value

        Returns:
            grip_type: String ('precision_pinch', 'power_grasp', etc.)
        """
        # Check thumb-index distance for precision pinch
        if 'THUMB_TIP' in hand_landmarks and 'INDEX_FINGER_TIP' in hand_landmarks:
            thumb = np.array([
                hand_landmarks['THUMB_TIP']['x'],
                hand_landmarks['THUMB_TIP']['y'],
                hand_landmarks['THUMB_TIP']['z']
            ])
            index = np.array([
                hand_landmarks['INDEX_FINGER_TIP']['x'],
                hand_landmarks['INDEX_FINGER_TIP']['y'],
                hand_landmarks['INDEX_FINGER_TIP']['z']
            ])

            distance = np.linalg.norm(thumb - index)

            # Check for tripod grip (thumb + index + middle close together)
            if 'MIDDLE_FINGER_TIP' in hand_landmarks:
                middle = np.array([
                    hand_landmarks['MIDDLE_FINGER_TIP']['x'],
                    hand_landmarks['MIDDLE_FINGER_TIP']['y'],
                    hand_landmarks['MIDDLE_FINGER_TIP']['z']
                ])

                thumb_middle_dist = np.linalg.norm(thumb - middle)

                if distance < 0.03 and thumb_middle_dist < 0.03:
                    return 'tripod_grip'

            # Precision pinch (just thumb + index)
            if distance < 0.02:
                return 'precision_pinch'

        # Power grasp (hand closed around object)
        if gripper_openness < 0.3:
            return 'power_grasp'

        return 'none'

    def detect_motion_pattern(self, trajectory, timestamps):
        """
        Classify motion pattern from trajectory

        Returns:
            pattern: Dict with type, amplitude, frequency
        """
        if len(trajectory) < 10:
            return {'type': 'insufficient_data'}

        trajectory = np.array(trajectory)

        # Compute motion statistics
        displacements = np.diff(trajectory, axis=0)
        speeds = np.linalg.norm(displacements, axis=1)

        mean_speed = np.mean(speeds)
        max_displacement = np.max(np.linalg.norm(trajectory - trajectory[0], axis=1))

        # Small amplitude = writing/typing
        if max_displacement < 0.05:
            return {
                'type': 'small_circular',
                'amplitude': max_displacement,
                'speed': mean_speed
            }

        # Check for circular motion (stirring)
        if self._is_circular_motion(trajectory):
            return {
                'type': 'circular',
                'radius': self._estimate_radius(trajectory),
                'speed': mean_speed
            }

        # Check for sawing motion (back and forth)
        if self._is_sawing_motion(trajectory):
            return {
                'type': 'sawing',
                'frequency': self._estimate_frequency(trajectory, timestamps),
                'speed': mean_speed
            }

        # Default: linear motion
        return {
            'type': 'linear',
            'displacement': max_displacement,
            'speed': mean_speed
        }

    def _is_circular_motion(self, trajectory):
        """Check if trajectory forms circular pattern"""
        # Compute center of mass
        center = np.mean(trajectory, axis=0)

        # Compute distances from center
        distances = np.linalg.norm(trajectory - center, axis=1)

        # Circular if std of distances is small (constant radius)
        return np.std(distances) / np.mean(distances) < 0.2

    def _estimate_radius(self, trajectory):
        """Estimate radius of circular motion"""
        center = np.mean(trajectory, axis=0)
        distances = np.linalg.norm(trajectory - center, axis=1)
        return np.mean(distances)

    def _is_sawing_motion(self, trajectory):
        """Check for repetitive back-and-forth motion"""
        # Project onto principal axis
        trajectory_centered = trajectory - np.mean(trajectory, axis=0)

        # Find direction of motion
        cov = np.cov(trajectory_centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        principal_axis = eigenvectors[:, np.argmax(eigenvalues)]

        # Project onto principal axis
        projections = trajectory_centered @ principal_axis

        # Count direction changes (back and forth)
        direction_changes = np.sum(np.diff(np.sign(np.diff(projections))) != 0)

        # Sawing motion has multiple direction changes
        return direction_changes >= 3

    def _estimate_frequency(self, trajectory, timestamps):
        """Estimate motion frequency (cycles per second)"""
        # Simple: count peaks in velocity
        velocities = np.diff(trajectory, axis=0)
        speeds = np.linalg.norm(velocities, axis=1)

        # Find peaks
        peaks = 0
        for i in range(1, len(speeds) - 1):
            if speeds[i] > speeds[i-1] and speeds[i] > speeds[i+1]:
                peaks += 1

        duration = timestamps[-1] - timestamps[0]
        return peaks / duration if duration > 0 else 0


# Example usage demonstrating deterministic detection
if __name__ == "__main__":
    print("=" * 80)
    print("CONTACT-BASED ACTION DETECTION (Deterministic)")
    print("=" * 80)

    print("\nAction Signatures Loaded:")
    detector = ContactBasedActionDetector()

    for action, signature in detector.ACTION_SIGNATURES.items():
        print(f"\n{action.upper()}:")
        print(f"  Grip: {signature.get('grip', 'N/A')}")
        print(f"  Objects: {signature.get('object_types', 'any')}")
        print(f"  Motion: {signature['motion']['type']}")
        print(f"  Description: {signature['description']}")

    print("\n" + "=" * 80)
    print("This is DETERMINISTIC - no neural networks, no hallucinations")
    print("Actions are defined by physics + biomechanics")
    print("=" * 80)
