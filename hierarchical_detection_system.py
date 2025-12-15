"""
HIERARCHICAL ACTION DETECTION SYSTEM

Architecture:
- Vision System: High-level action authority (WHAT action)
- Physics System: Low-level kinematic authority (HOW it moves)

Philosophy:
- Vision sees the semantic action (PULL, PUSH, etc.)
- Physics measures the exact execution (trajectory, forces)
- Robot needs BOTH: action label + execution data
"""

import json
import numpy as np
from pathlib import Path


class HierarchicalActionDetector:
    """
    Two-level detection system:
    Level 1: Physics extracts kinematics (ALWAYS)
    Level 2: Vision classifies action (WHEN AMBIGUOUS)
    """

    def __init__(self, physics_detector, vision_detector=None):
        self.physics = physics_detector
        self.vision = vision_detector

        # Confidence thresholds
        self.PHYSICS_CONFIDENCE_THRESHOLD = 0.7
        self.AMBIGUITY_THRESHOLD = 0.15  # If actions are within 15% score, it's ambiguous

    def detect(self, metric_file, extraction_file, video_file=None):
        """
        Hierarchical detection with vision override

        Returns:
            robot_data: Dict with action label + kinematic data
        """
        print("\n" + "="*70)
        print("HIERARCHICAL ACTION DETECTION")
        print("="*70)
        print()

        # LEVEL 1: Physics extracts kinematics (ALWAYS)
        print("📊 LEVEL 1: Physics Analysis")
        print("-" * 70)

        physics_actions = self.physics.detect_actions(metric_file, extraction_file)

        # Extract kinematic data
        with open(metric_file, 'r') as f:
            metric_data = json.load(f)

        kinematics = self._extract_kinematics(metric_data)

        print(f"✅ Kinematic data extracted: {len(kinematics['positions'])} frames")
        print(f"📍 Physics detected {len(physics_actions)} actions")
        for action in physics_actions:
            print(f"   - {action['action'].upper()}: {action['start_time']:.2f}s - {action['end_time']:.2f}s (confidence: {action['confidence']:.0%})")
        print()

        # LEVEL 2: Check if physics is confident
        decision = self._analyze_physics_confidence(physics_actions)

        print("🤔 LEVEL 2: Confidence Analysis")
        print("-" * 70)
        print(f"Status: {decision['status']}")
        print(f"Reason: {decision['reason']}")
        print()

        # LEVEL 3: Decide if vision is needed
        if decision['status'] == 'CONFIDENT':
            # Physics is clear
            print("✅ Physics is confident → Using physics result")
            final_action = decision['action']
            method = 'physics'
            vision_result = None

        elif decision['status'] == 'AMBIGUOUS':
            # Physics confused → use vision
            print("⚠️  Physics is ambiguous → Requesting vision analysis")

            if self.vision is None or video_file is None:
                print("❌ Vision system not available → Using physics best guess")
                final_action = decision['action']
                method = 'physics_fallback'
                vision_result = None
            else:
                print("🔍 Vision system analyzing...")
                vision_result = self.vision.classify_action(video_file, kinematics, physics_actions)
                # Vision returns action name, convert to full action dict
                final_action = {
                    'action': vision_result['action'],
                    'start_time': physics_actions[0]['start_time'],
                    'end_time': physics_actions[-1]['end_time'],
                    'duration': physics_actions[-1]['end_time'] - physics_actions[0]['start_time'],
                    'confidence': vision_result['confidence']
                }
                method = 'vision_override'
                print(f"✅ Vision determined: {vision_result['action'].upper()} (confidence: {vision_result['confidence']:.0%})")

        else:  # UNCLEAR
            print("❌ Physics could not determine action → Vision required")

            if self.vision is None or video_file is None:
                print("❌ Vision system not available → No action detected")
                return None
            else:
                vision_result = self.vision.classify_action(video_file, kinematics, physics_actions)
                final_action = {
                    'action': vision_result['action'],
                    'start_time': 0,
                    'end_time': kinematics['timestamps'][-1],
                    'duration': kinematics['timestamps'][-1],
                    'confidence': vision_result['confidence']
                }
                method = 'vision_only'

        print()
        print("="*70)
        print("FINAL RESULT")
        print("="*70)
        print(f"Action: {final_action['action'].upper()}")
        print(f"Time: {final_action['start_time']:.2f}s - {final_action['end_time']:.2f}s")
        print(f"Duration: {final_action['duration']:.2f}s")
        print(f"Method: {method}")
        print(f"Confidence: {final_action['confidence']:.0%}")
        print()

        # LEVEL 4: Generate robot data
        robot_data = {
            'action_label': final_action['action'],
            'start_time': final_action['start_time'],
            'end_time': final_action['end_time'],
            'duration': final_action['duration'],
            'trajectory': kinematics['positions'],
            'velocities': kinematics['velocities'],
            'accelerations': kinematics['accelerations'],
            'gripper_states': kinematics['gripper_openness'],
            'timestamps': kinematics['timestamps'],
            'confidence': final_action['confidence'],
            'detection_method': method,
            'metadata': {
                'physics_detections': physics_actions,
                'vision_result': vision_result,
                'decision': decision
            }
        }

        return robot_data

    def _extract_kinematics(self, metric_data):
        """
        Extract raw kinematic data (physics authority)
        """
        timesteps = metric_data['timesteps']

        return {
            'timestamps': [ts['timestamp'] for ts in timesteps],
            'positions': [ts['observations']['end_effector_pos_metric'] for ts in timesteps],
            'velocities': [ts['kinematics']['velocity'] for ts in timesteps],
            'accelerations': [ts['kinematics']['acceleration'] for ts in timesteps],
            'gripper_openness': [ts['observations']['gripper_openness'] for ts in timesteps]
        }

    def _analyze_physics_confidence(self, physics_actions):
        """
        Determine if physics result is confident, ambiguous, or unclear
        """
        if len(physics_actions) == 0:
            return {
                'status': 'UNCLEAR',
                'reason': 'No actions detected by physics',
                'action': None
            }

        # Check for conflicting actions (PUSH + PULL)
        action_types = [a['action'] for a in physics_actions]

        # Check for PUSH/PULL conflict
        has_push = 'push' in action_types
        has_pull = 'pull' in action_types

        if has_push and has_pull:
            return {
                'status': 'AMBIGUOUS',
                'reason': 'Both PUSH and PULL detected (conflicting)',
                'action': physics_actions[0]  # Best guess
            }

        # Check for low confidence
        primary_action = physics_actions[0]
        if primary_action['confidence'] < self.PHYSICS_CONFIDENCE_THRESHOLD:
            return {
                'status': 'AMBIGUOUS',
                'reason': f"Low confidence ({primary_action['confidence']:.0%} < {self.PHYSICS_CONFIDENCE_THRESHOLD:.0%})",
                'action': primary_action
            }

        # Check for multiple actions with similar confidence
        if len(physics_actions) > 1:
            conf_diff = physics_actions[0]['confidence'] - physics_actions[1]['confidence']
            if conf_diff < self.AMBIGUITY_THRESHOLD:
                return {
                    'status': 'AMBIGUOUS',
                    'reason': f"Multiple actions with similar confidence (diff: {conf_diff:.0%})",
                    'action': physics_actions[0]
                }

        # Physics is confident
        return {
            'status': 'CONFIDENT',
            'reason': f"Clear detection with {primary_action['confidence']:.0%} confidence",
            'action': primary_action
        }


class VisionActionClassifier:
    """
    Vision-based action classifier (to be implemented with Claude API or other vision model)
    """

    def classify_action(self, video_file, kinematics, physics_suggestions):
        """
        Classify action using vision analysis

        Args:
            video_file: Path to video
            kinematics: Physics kinematic data
            physics_suggestions: What physics detected

        Returns:
            action_dict with vision's classification
        """
        # TODO: Implement with Claude Vision API or other vision model
        # For now, this is a placeholder

        print("🔮 Vision classifier called (placeholder)")
        print(f"   Video: {video_file}")
        print(f"   Physics suggested: {[a['action'] for a in physics_suggestions]}")

        # Placeholder: Return physics best guess for now
        # In real implementation, this would:
        # 1. Extract key frames from video
        # 2. Send to Claude Vision API
        # 3. Ask: "What action is being performed?"
        # 4. Return vision's classification

        return {
            'action': physics_suggestions[0]['action'],
            'confidence': 0.85,
            'method': 'vision_placeholder',
            'reasoning': 'Vision classifier not yet implemented'
        }


def main():
    import sys
    from advanced_action_detection import AdvancedActionDetector

    if len(sys.argv) < 3:
        print("Usage: python hierarchical_detection_system.py <metric_3d.json> <extraction_with_orientation.json> [video.mov]")
        return

    metric_file = sys.argv[1]
    extraction_file = sys.argv[2]
    video_file = sys.argv[3] if len(sys.argv) > 3 else None

    # Initialize systems
    physics_detector = AdvancedActionDetector()
    vision_detector = VisionActionClassifier()  # Placeholder for now

    # Create hierarchical detector
    detector = HierarchicalActionDetector(physics_detector, vision_detector)

    # Run detection
    robot_data = detector.detect(metric_file, extraction_file, video_file)

    # Save robot data
    if robot_data:
        output_file = Path(metric_file).stem + '_robot_data.json'
        with open(output_file, 'w') as f:
            json.dump(robot_data, f, indent=2)

        print(f"\n💾 Robot data saved to: {output_file}")


if __name__ == "__main__":
    main()
