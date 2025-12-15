================================================================================
SMART RECONCILIATION JUNCTION - PERFORMANCE REPORT
================================================================================

Total videos tested: 8
Smart decisions: 8/8 (10000%)
Conflicts detected: 8/8 (10000%)
Physics wins: 3 (3750%)
Vision wins: 5 (6250%)

================================================================================
DETAILED RESULTS
================================================================================

VIDEO #02:
  Winner: VISION
  Final Action: OPEN (discarded: pull)
  Confidence: 6669%
  Method: vision_smart
  Scores: Physics=3.27, Vision=6.51
  Reasoning: Both actions physically plausible | Physics expert on pull (90%) | Vision expert on open (70%) | ...

VIDEO #03:
  Winner: VISION
  Final Action: POUR (discarded: push)
  Confidence: 6156%
  Method: vision_smart
  Scores: Physics=3.27, Vision=7.99
  Reasoning: Vision validated by data, physics contradicted | Physics expert on push (90%) | Vision correctly ...

VIDEO #04:
  Winner: VISION
  Final Action: OPEN (discarded: pour)
  Confidence: 6669%
  Method: vision_smart
  Scores: Physics=4.96, Vision=5.51
  Reasoning: Both actions physically plausible | Physics expert on pour (85%) | Vision expert on open (70%) | ...

VIDEO #05:
  Winner: PHYSICS
  Final Action: POUR (discarded: lift)
  Confidence: 8132%
  Method: physics_smart
  Scores: Physics=4.96, Vision=2.35
  Reasoning: Both actions physically plausible | Physics expert on pour (85%)

VIDEO #06:
  Winner: VISION
  Final Action: OPEN (discarded: pull)
  Confidence: 6669%
  Method: vision_smart
  Scores: Physics=3.27, Vision=5.01
  Reasoning: Both actions physically plausible | Physics expert on pull (90%) | Vision expert on open (70%) | ...

VIDEO #07:
  Winner: VISION
  Final Action: OPEN (discarded: pour)
  Confidence: 6669%
  Method: vision_smart
  Scores: Physics=4.96, Vision=5.51
  Reasoning: Both actions physically plausible | Physics expert on pour (85%) | Vision expert on open (70%) | ...

VIDEO #08:
  Winner: PHYSICS
  Final Action: PULL (discarded: place)
  Confidence: 8550%
  Method: physics_smart
  Scores: Physics=3.27, Vision=2.35
  Reasoning: Both actions physically plausible | Physics expert on pull (90%)

VIDEO #09:
  Winner: PHYSICS
  Final Action: PULL (discarded: lift)
  Confidence: 8550%
  Method: physics_smart
  Scores: Physics=5.27, Vision=2.35
  Reasoning: Physics validated by data, vision contradicted | Physics expert on pull (90%)

================================================================================
DECISION PATTERNS
================================================================================

When Physics Won:
  Video #05: POUR - Both actions physically plausible | Physics expert on pour (...
  Video #08: PULL - Both actions physically plausible | Physics expert on pull (...
  Video #09: PULL - Physics validated by data, vision contradicted | Physics exp...

When Vision Won:
  Video #02: OPEN - Both actions physically plausible | Physics expert on pull (...
  Video #03: POUR - Vision validated by data, physics contradicted | Physics exp...
  Video #04: OPEN - Both actions physically plausible | Physics expert on pour (...
  Video #06: OPEN - Both actions physically plausible | Physics expert on pull (...
  Video #07: OPEN - Both actions physically plausible | Physics expert on pour (...