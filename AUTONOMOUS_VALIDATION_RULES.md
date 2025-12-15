# AUTONOMOUS VALIDATION RULES
## "What determines the need for Level 3 vision verification?"

---

## THE PROBLEM

**Current System**: Human validates when physics is uncertain
- Human watches video
- Human confirms: "Yes, this was a PULL"
- System learns and adjusts

**Goal**: Make this **fully autonomous** - no human validation needed

---

## SOLUTION: Objective Physics-Based Validation Rules

### The Insight:

**Physics doesn't lie - we just need better rules to interpret it!**

Instead of asking a human "was this a PULL?", we can use **physics consistency checks**:

---

## VALIDATION RULE 1: Net Displacement Check

**Principle**: If user "pulled" object, the net displacement should be backward (toward body)

```python
def check_net_displacement(positions):
    """
    Check if net motion matches detected action
    """
    start_pos = positions[0]
    end_pos = positions[-1]

    net_displacement = end_pos - start_pos

    # Z-axis: negative = forward, positive = backward
    net_z = net_displacement[2]

    if net_z > 0.1:
        # Net backward motion > 10cm
        return 'PULL'
    elif net_z < -0.1:
        # Net forward motion > 10cm
        return 'PUSH'
    else:
        # No significant net motion
        return 'AMBIGUOUS'
```

**For Video #9**:
```
Start Z: 0.8
End Z: 0.3
Net Z: -0.5 (FORWARD!)

Physics velocity: 38% forward, 37% backward
Net displacement: FORWARD

Conclusion: This is actually PUSH, not PULL!
OR: The reference frame is wrong
```

**Validation Trigger**:
```python
if detected_action == 'PULL' and net_displacement_z < 0:
    # Conflict! Says PULL but moved forward
    TRIGGER_LEVEL_3 = True
```

---

## VALIDATION RULE 2: Velocity-Displacement Consistency

**Principle**: Velocity integral should match displacement

```python
def check_consistency(velocities, positions, timestamps):
    """
    Physics consistency check:
    ∫velocity dt should equal displacement
    """
    # Compute displacement from velocity integration
    dt = np.diff(timestamps)
    integrated_displacement = np.sum(velocities[:-1] * dt[:, np.newaxis], axis=0)

    # Compute actual displacement
    actual_displacement = positions[-1] - positions[0]

    # Check consistency
    error = np.linalg.norm(integrated_displacement - actual_displacement)

    if error > 0.5:
        # Large inconsistency → possible tracking error or reference frame issue
        return {
            'consistent': False,
            'error': error,
            'reason': 'Velocity integration does not match displacement - possible reference frame issue',
            'trigger_vision': True
        }
    else:
        return {
            'consistent': True,
            'error': error,
            'trigger_vision': False
        }
```

**When this triggers**: Camera movement, tracking errors, reference frame issues

---

## VALIDATION RULE 3: Action-Duration Plausibility

**Principle**: Each action has a typical duration range

```python
ACTION_DURATION_RANGES = {
    'PUSH': (0.5, 5.0),    # Pushing takes 0.5-5 seconds
    'PULL': (0.5, 5.0),    # Pulling takes 0.5-5 seconds
    'LIFT': (0.3, 3.0),    # Lifting is faster
    'PLACE': (0.3, 3.0),   # Placing is quick
    'TWIST': (0.2, 2.0),   # Twisting is brief
    'POUR': (1.0, 10.0),   # Pouring takes time
}

def check_duration_plausibility(action, duration):
    """
    Check if detected action duration makes sense
    """
    min_dur, max_dur = ACTION_DURATION_RANGES[action]

    if duration < min_dur:
        return {
            'plausible': False,
            'reason': f'{action} detected in {duration:.2f}s (too fast, min {min_dur}s)',
            'trigger_vision': True
        }
    elif duration > max_dur:
        return {
            'plausible': False,
            'reason': f'{action} detected in {duration:.2f}s (too slow, max {max_dur}s)',
            'trigger_vision': True
        }
    else:
        return {'plausible': True, 'trigger_vision': False}
```

**Example**: If system detects "TWIST" lasting 10 seconds → unlikely, trigger vision check

---

## VALIDATION RULE 4: Conflicting Actions Check

**Principle**: Certain actions cannot happen simultaneously

```python
CONFLICTING_ACTIONS = {
    'PUSH': ['PULL'],          # Can't push and pull at same time
    'LIFT': ['PLACE'],         # Can't lift and place simultaneously
    'TWIST_OPEN': ['TWIST_CLOSE'],
}

def check_conflicting_actions(detected_actions):
    """
    Check for physically impossible action combinations
    """
    action_types = [a['action'] for a in detected_actions]

    conflicts = []
    for action in action_types:
        if action in CONFLICTING_ACTIONS:
            conflicting = CONFLICTING_ACTIONS[action]
            for conflict in conflicting:
                if conflict in action_types:
                    conflicts.append((action, conflict))

    if conflicts:
        return {
            'has_conflicts': True,
            'conflicts': conflicts,
            'reason': f'Detected both {conflicts[0][0]} and {conflicts[0][1]} - impossible!',
            'trigger_vision': True
        }

    return {'has_conflicts': False, 'trigger_vision': False}
```

**Video #9 Example**:
```
Detected: PUSH + PULL
Conflict: YES (can't do both)
Trigger: LEVEL 3
```

---

## VALIDATION RULE 5: Hand State Consistency

**Principle**: Hand state should match action type

```python
def check_hand_state_consistency(action, openness_data):
    """
    Verify hand state makes sense for detected action
    """
    mean_openness = np.mean(openness_data)

    EXPECTED_STATES = {
        'PUSH': (0.0, 0.5),    # Hand closed or semi-closed (contacting object)
        'PULL': (0.0, 0.4),    # Hand closed (grasping)
        'LIFT': (0.0, 0.3),    # Hand closed (grasping)
        'PLACE': (0.3, 1.0),   # Hand opens during/after placement
        'TWIST': (0.0, 0.3),   # Hand closed (grasping to twist)
        'POUR': (0.0, 0.4),    # Hand closed (holding container)
    }

    if action in EXPECTED_STATES:
        min_open, max_open = EXPECTED_STATES[action]

        if min_open <= mean_openness <= max_open:
            return {'consistent': True, 'trigger_vision': False}
        else:
            return {
                'consistent': False,
                'reason': f'{action} detected but hand openness ({mean_openness:.2f}) outside expected range ({min_open}-{max_open})',
                'trigger_vision': True
            }

    return {'consistent': True, 'trigger_vision': False}
```

**Example**: If "PULL" detected but hand is fully open (0.9) → unlikely, trigger vision

---

## VALIDATION RULE 6: Velocity Pattern Signature

**Principle**: Each action has a characteristic velocity pattern

```python
def compute_velocity_signature(velocities):
    """
    Compute statistical signature of velocity pattern
    """
    return {
        'mean': np.mean(velocities, axis=0),
        'std': np.std(velocities, axis=0),
        'max': np.max(np.abs(velocities), axis=0),
        'direction_changes': np.sum(np.diff(np.sign(velocities), axis=0) != 0, axis=0)
    }

def check_velocity_signature_match(action, signature):
    """
    Check if velocity signature matches expected pattern for action
    """
    # PUSH: Should have dominant forward velocity, low direction changes
    if action == 'PUSH':
        if signature['mean'][2] > -0.5 and signature['direction_changes'][2] < 10:
            return {'matches': True, 'trigger_vision': False}
        else:
            return {
                'matches': False,
                'reason': f'PUSH detected but velocity pattern inconsistent (mean Z={signature["mean"][2]:.2f}, changes={signature["direction_changes"][2]})',
                'trigger_vision': True
            }

    # PULL: Should have dominant backward velocity
    if action == 'PULL':
        if signature['mean'][2] > 0.5 and signature['direction_changes'][2] < 10:
            return {'matches': True, 'trigger_vision': False}
        else:
            return {
                'matches': False,
                'reason': f'PULL detected but velocity pattern inconsistent (mean Z={signature["mean"][2]:.2f})',
                'trigger_vision': True
            }

    # ... more action patterns
```

**Video #9 Example**:
```
Action detected: PULL
Mean Z-velocity: -0.04 (slightly forward, not backward!)
Direction changes: 180+ (oscillating back and forth)

Signature match: NO
Trigger: LEVEL 3
```

---

## INTEGRATED AUTONOMOUS VALIDATION SYSTEM

```python
class AutonomousValidator:
    """
    Autonomous validation system - no human needed!
    """

    def validate(self, detected_actions, kinematics):
        """
        Run all validation rules to determine if Level 3 is needed
        """
        triggers = []

        # Rule 1: Net displacement check
        net_disp_check = self.check_net_displacement(
            detected_actions,
            kinematics['positions']
        )
        if net_disp_check['trigger_vision']:
            triggers.append(net_disp_check)

        # Rule 2: Velocity-displacement consistency
        consistency_check = self.check_consistency(
            kinematics['velocities'],
            kinematics['positions'],
            kinematics['timestamps']
        )
        if consistency_check['trigger_vision']:
            triggers.append(consistency_check)

        # Rule 3: Duration plausibility
        for action in detected_actions:
            duration_check = self.check_duration_plausibility(
                action['action'],
                action['duration']
            )
            if duration_check['trigger_vision']:
                triggers.append(duration_check)

        # Rule 4: Conflicting actions
        conflict_check = self.check_conflicting_actions(detected_actions)
        if conflict_check['trigger_vision']:
            triggers.append(conflict_check)

        # Rule 5: Hand state consistency
        for action in detected_actions:
            hand_check = self.check_hand_state_consistency(
                action['action'],
                kinematics['gripper_openness']
            )
            if hand_check['trigger_vision']:
                triggers.append(hand_check)

        # Rule 6: Velocity signature
        signature = self.compute_velocity_signature(kinematics['velocities'])
        for action in detected_actions:
            sig_check = self.check_velocity_signature_match(
                action['action'],
                signature
            )
            if sig_check['trigger_vision']:
                triggers.append(sig_check)

        # Decision
        if len(triggers) == 0:
            return {
                'needs_level_3': False,
                'confidence': 'HIGH',
                'reason': 'All validation rules passed'
            }
        elif len(triggers) <= 2:
            return {
                'needs_level_3': True,
                'confidence': 'MEDIUM',
                'reason': f'{len(triggers)} validation rules triggered',
                'triggers': triggers
            }
        else:
            return {
                'needs_level_3': True,
                'confidence': 'LOW',
                'reason': f'{len(triggers)} validation rules triggered (high uncertainty)',
                'triggers': triggers
            }
```

---

## HOW THIS WORKS IN VIDEO #9

### Physics Detects:
```
Actions: PUSH + PULL
Duration: 3s, 3s, 4.5s
Velocities: 38% forward, 37% backward
Net displacement: -0.5 (forward)
Hand state: 0.28 (closed)
```

### Autonomous Validation Runs:

**Rule 1 - Net Displacement**:
```
✅ TRIGGER: PULL detected but net displacement is FORWARD (-0.5)
Reason: "Action says PULL but object moved forward"
```

**Rule 4 - Conflicting Actions**:
```
✅ TRIGGER: Both PUSH and PULL detected
Reason: "Physically impossible to do both simultaneously"
```

**Rule 6 - Velocity Signature**:
```
✅ TRIGGER: PULL detected but mean Z-velocity is -0.04 (forward)
Reason: "Velocity pattern inconsistent with PULL"
```

### Decision:
```
needs_level_3: TRUE
confidence: LOW
triggers: 3/6 rules triggered
reason: "Multiple validation rules failed - vision verification required"
```

### Vision Analyzes → Determines PULL → Robot gets correct data!

---

## THE BEAUTY: FULLY AUTONOMOUS!

```
Physics detects → Validation rules check → Auto-trigger Level 3 → Vision corrects
                         ↑                                              ↓
                  NO HUMAN NEEDED!                            Robot gets clean data
```

**No human validation required** - the system checks itself using **physics consistency rules**!

---

## NEXT STEP: IMPLEMENT THIS

Would you like me to implement the `AutonomousValidator` class and integrate it into the hierarchical system?

This would make Video #10 testing **fully autonomous** - the system would automatically know when to use vision verification!
