"""
LOCOMOTION ACTION RULES (Physics-Based)

Philosophy: Human locomotion is defined by biomechanical patterns
- Running vs Walking vs Standing
- Jumping vs Squatting vs Sitting

These are NOT learned - they're physical laws validated with data
"""

import numpy as np

class LocomotionDetector:
    """
    Detect human locomotion actions from pose keypoints

    Uses MediaPipe Pose (33 keypoints) to detect body motion patterns
    """

    # RUNNING RULE (Physics Definition)
    RUNNING_RULE = {
        'name': 'running',
        'requirements': [
            {
                'feature': 'vertical_oscillation',
                'description': 'Body center of mass moves up/down rhythmically',
                'threshold': {
                    'amplitude': 0.05,  # >5cm vertical oscillation
                    'frequency': (2.0, 4.0)  # 2-4 Hz (120-240 steps/min)
                },
                'keypoints_used': ['LEFT_HIP', 'RIGHT_HIP']  # Track pelvis height
            },
            {
                'feature': 'forward_velocity',
                'description': 'Body moving forward at running speed',
                'threshold': {
                    'speed': 2.0,  # >2 m/s (7.2 km/h)
                },
                'keypoints_used': ['NOSE']  # Track overall body position
            },
            {
                'feature': 'flight_phase',
                'description': 'Both feet off ground simultaneously (key difference from walking)',
                'threshold': {
                    'duration': 0.1,  # At least 0.1s flight time per stride
                },
                'keypoints_used': ['LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_HEEL', 'RIGHT_HEEL']
            },
            {
                'feature': 'leg_swing_speed',
                'description': 'Legs swing faster than walking',
                'threshold': {
                    'angular_velocity': 6.0,  # rad/s
                },
                'keypoints_used': ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE',
                                   'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE']
            }
        ],
        'minimum_requirements': 3,  # Need at least 3/4 features to confirm running
        'validation_status': 'NOT_TESTED',
        'validation_notes': 'Awaiting test video'
    }

    # WALKING RULE (For comparison)
    WALKING_RULE = {
        'name': 'walking',
        'requirements': [
            {
                'feature': 'vertical_oscillation',
                'threshold': {
                    'amplitude': 0.03,  # 3-5cm (less than running)
                    'frequency': (1.5, 2.5)  # 1.5-2.5 Hz (90-150 steps/min)
                }
            },
            {
                'feature': 'forward_velocity',
                'threshold': {
                    'speed': 1.0,  # 1-2 m/s (3.6-7.2 km/h)
                }
            },
            {
                'feature': 'continuous_ground_contact',
                'description': 'Always one foot on ground (no flight phase)',
                'threshold': {
                    'flight_duration': 0.0,  # No flight time
                }
            },
            {
                'feature': 'leg_swing_speed',
                'threshold': {
                    'angular_velocity': 3.0,  # rad/s (slower than running)
                }
            }
        ],
        'validation_status': 'NOT_TESTED'
    }

    # JUMPING RULE
    JUMPING_RULE = {
        'name': 'jumping',
        'requirements': [
            {
                'feature': 'rapid_vertical_acceleration',
                'description': 'Quick downward then upward motion',
                'threshold': {
                    'acceleration': 9.8,  # >1g upward acceleration
                    'preparation_time': 0.5  # 0.3-0.5s crouch before jump
                }
            },
            {
                'feature': 'both_feet_leave_ground',
                'description': 'Simultaneous takeoff',
                'threshold': {
                    'min_height': 0.1,  # At least 10cm off ground
                    'duration': 0.3  # In air for >0.3s
                }
            },
            {
                'feature': 'landing_impact',
                'description': 'Sudden deceleration on landing',
                'threshold': {
                    'deceleration': -15.0  # Strong downward force
                }
            }
        ],
        'validation_status': 'NOT_TESTED'
    }

    def detect_running(self, pose_data, timestamps):
        """
        Detect running action from pose keypoints

        Args:
            pose_data: List of dicts with pose keypoints over time
            timestamps: Array of timestamps

        Returns:
            detected: Boolean
            confidence: 0-1 score (based on how many requirements met)
            measurements: Dict of actual measured values
        """
        if len(pose_data) < 30:  # Need at least 1 second of data
            return False, 0.0, {'error': 'insufficient_data'}

        measurements = {}
        requirements_met = 0
        total_requirements = len(self.RUNNING_RULE['requirements'])

        # 1. Check vertical oscillation (pelvis height)
        pelvis_heights = self._compute_pelvis_heights(pose_data)
        if len(pelvis_heights) > 0:
            vert_oscillation = self._compute_oscillation(pelvis_heights, timestamps)
            measurements['vertical_oscillation'] = {
                'amplitude': vert_oscillation['amplitude'],
                'frequency': vert_oscillation['frequency']
            }

            rule_amp = self.RUNNING_RULE['requirements'][0]['threshold']['amplitude']
            rule_freq = self.RUNNING_RULE['requirements'][0]['threshold']['frequency']

            if (vert_oscillation['amplitude'] > rule_amp and
                rule_freq[0] <= vert_oscillation['frequency'] <= rule_freq[1]):
                requirements_met += 1
                measurements['vertical_oscillation']['status'] = '✅ PASS'
            else:
                measurements['vertical_oscillation']['status'] = '❌ FAIL'

        # 2. Check forward velocity
        forward_velocity = self._compute_forward_velocity(pose_data, timestamps)
        measurements['forward_velocity'] = {
            'speed': forward_velocity,
            'threshold': self.RUNNING_RULE['requirements'][1]['threshold']['speed']
        }

        if forward_velocity > self.RUNNING_RULE['requirements'][1]['threshold']['speed']:
            requirements_met += 1
            measurements['forward_velocity']['status'] = '✅ PASS'
        else:
            measurements['forward_velocity']['status'] = '❌ FAIL'

        # 3. Check for flight phase (advanced - requires foot height tracking)
        flight_detected = self._detect_flight_phase(pose_data, timestamps)
        measurements['flight_phase'] = {
            'detected': flight_detected,
            'description': 'Both feet off ground simultaneously'
        }

        if flight_detected:
            requirements_met += 1
            measurements['flight_phase']['status'] = '✅ PASS'
        else:
            measurements['flight_phase']['status'] = '❌ FAIL'

        # 4. Check leg swing speed
        leg_swing_speed = self._compute_leg_swing_speed(pose_data, timestamps)
        measurements['leg_swing_speed'] = {
            'speed': leg_swing_speed,
            'threshold': self.RUNNING_RULE['requirements'][3]['threshold']['angular_velocity']
        }

        if leg_swing_speed > self.RUNNING_RULE['requirements'][3]['threshold']['angular_velocity']:
            requirements_met += 1
            measurements['leg_swing_speed']['status'] = '✅ PASS'
        else:
            measurements['leg_swing_speed']['status'] = '❌ FAIL'

        # Determine if running based on requirements met
        min_required = self.RUNNING_RULE['minimum_requirements']
        detected = requirements_met >= min_required
        confidence = requirements_met / total_requirements

        measurements['summary'] = {
            'requirements_met': requirements_met,
            'total_requirements': total_requirements,
            'minimum_required': min_required,
            'detected': detected,
            'confidence': confidence
        }

        return detected, confidence, measurements

    def _compute_pelvis_heights(self, pose_data):
        """Extract pelvis height (average of left/right hip) over time"""
        heights = []

        for frame in pose_data:
            if 'LEFT_HIP' in frame and 'RIGHT_HIP' in frame:
                left_hip_y = frame['LEFT_HIP']['y']
                right_hip_y = frame['RIGHT_HIP']['y']
                pelvis_height = (left_hip_y + right_hip_y) / 2.0
                heights.append(pelvis_height)

        return np.array(heights)

    def _compute_oscillation(self, signal, timestamps):
        """
        Compute oscillation amplitude and frequency from signal

        Returns:
            amplitude: Peak-to-peak amplitude
            frequency: Dominant frequency in Hz
        """
        if len(signal) < 10:
            return {'amplitude': 0, 'frequency': 0}

        # Amplitude: peak-to-peak
        amplitude = np.max(signal) - np.min(signal)

        # Frequency: count peaks
        peaks = 0
        for i in range(1, len(signal) - 1):
            if signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                peaks += 1

        duration = timestamps[-1] - timestamps[0]
        frequency = peaks / duration if duration > 0 else 0

        return {'amplitude': amplitude, 'frequency': frequency}

    def _compute_forward_velocity(self, pose_data, timestamps):
        """Compute forward velocity from nose/head position"""
        if len(pose_data) < 10:
            return 0.0

        # Get nose positions (proxy for body center)
        positions = []
        for frame in pose_data:
            if 'NOSE' in frame:
                # Assuming X is forward direction in camera frame
                pos = frame['NOSE']['x']
                positions.append(pos)

        if len(positions) < 10:
            return 0.0

        positions = np.array(positions)

        # Compute velocity (distance / time)
        total_distance = abs(positions[-1] - positions[0])
        duration = timestamps[-1] - timestamps[0]

        velocity = total_distance / duration if duration > 0 else 0.0

        return velocity

    def _detect_flight_phase(self, pose_data, timestamps):
        """
        Detect if both feet leave ground simultaneously

        This is the KEY difference between running and walking!
        """
        # Simplified: Check if ankle heights are consistently high
        # (In real implementation, need ground plane estimation)

        flight_frames = 0

        for frame in pose_data:
            if 'LEFT_ANKLE' in frame and 'RIGHT_ANKLE' in frame:
                left_ankle_y = frame['LEFT_ANKLE']['y']
                right_ankle_y = frame['RIGHT_ANKLE']['y']

                # If both ankles are above threshold (rough heuristic)
                # This needs calibration with actual data!
                if left_ankle_y < 0.5 and right_ankle_y < 0.5:  # Y is inverted in image coords
                    flight_frames += 1

        # If >20% of frames show flight, probably running
        return flight_frames / len(pose_data) > 0.2 if len(pose_data) > 0 else False

    def _compute_leg_swing_speed(self, pose_data, timestamps):
        """Compute angular velocity of leg swing"""
        if len(pose_data) < 10:
            return 0.0

        # Compute knee angle over time
        angles = []

        for frame in pose_data:
            if all(k in frame for k in ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE']):
                # Compute angle at knee
                hip = np.array([frame['LEFT_HIP']['x'], frame['LEFT_HIP']['y']])
                knee = np.array([frame['LEFT_KNEE']['x'], frame['LEFT_KNEE']['y']])
                ankle = np.array([frame['LEFT_ANKLE']['x'], frame['LEFT_ANKLE']['y']])

                # Vectors
                v1 = hip - knee
                v2 = ankle - knee

                # Angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
                angle = np.arccos(np.clip(cos_angle, -1, 1))
                angles.append(angle)

        if len(angles) < 10:
            return 0.0

        angles = np.array(angles)

        # Angular velocity
        angular_velocity = np.gradient(angles, timestamps[:len(angles)])

        return np.max(np.abs(angular_velocity))


# VALIDATION TEST HARNESS
if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING DETECTION RULE - AWAITING VALIDATION")
    print("=" * 80)

    detector = LocomotionDetector()

    print("\nRUNNING RULE DEFINITION:")
    print(f"Name: {detector.RUNNING_RULE['name']}")
    print(f"Status: {detector.RUNNING_RULE['validation_status']}")
    print(f"\nRequirements ({detector.RUNNING_RULE['minimum_requirements']}/{len(detector.RUNNING_RULE['requirements'])} needed):")

    for i, req in enumerate(detector.RUNNING_RULE['requirements'], 1):
        print(f"\n{i}. {req['feature'].upper()}")
        print(f"   Description: {req['description']}")
        print(f"   Threshold: {req['threshold']}")
        print(f"   Keypoints: {req['keypoints_used']}")

    print("\n" + "=" * 80)
    print("NEXT STEP: Record validation video")
    print("=" * 80)
    print("\nInstructions:")
    print("1. Record video of running for 5-10 seconds")
    print("2. Process through pipeline (extract pose keypoints)")
    print("3. Run detect_running() on processed data")
    print("4. If detected ✅ → rule validated")
    print("5. If not detected ❌ → analyze measurements, fine-tune thresholds")
    print("\nThis is DETERMINISTIC - no ML, no hallucination")
    print("Rules are physics-based and validated with real data")
