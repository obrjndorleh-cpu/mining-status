"""
Generate comprehensive report on smart junction performance
"""

import json
from pathlib import Path

def analyze_smart_junction_results():
    """Analyze all test results and generate report"""

    output_dir = Path('output')
    videos = [
        'test_video_02', 'test_video_03', 'test_video_04', 'test_video_05',
        'test_video_06', 'test_video_07', 'test_video_08', 'test_video_09'
    ]

    results = []

    for video in videos:
        reconciled_file = output_dir / f"{video}_reconciled.json"

        if not reconciled_file.exists():
            continue

        with open(reconciled_file, 'r') as f:
            data = json.load(f)

        results.append({
            'video': video,
            'action': data.get('action', 'unknown'),
            'confidence': data.get('confidence', 0.0),
            'method': data.get('method', 'unknown'),
            'reasoning': data.get('reasoning', ''),
            'conflict': data.get('conflict_detected', False),
            'discarded': data.get('discarded', None),
            'scores': data.get('scores', {}),
            'intelligence': data.get('intelligence_level', 'basic')
        })

    # Generate report
    report = []
    report.append("="*80)
    report.append("SMART RECONCILIATION JUNCTION - PERFORMANCE REPORT")
    report.append("="*80)
    report.append("")

    # Summary statistics
    smart_decisions = [r for r in results if r['intelligence'] == 'smart']
    conflicts = [r for r in results if r['conflict']]
    physics_wins = [r for r in results if 'physics' in r['method']]
    vision_wins = [r for r in results if 'vision' in r['method']]

    report.append(f"Total videos tested: {len(results)}")
    report.append(f"Smart decisions: {len(smart_decisions)}/{len(results)} ({len(smart_decisions)/len(results)*100:.0%})")
    report.append(f"Conflicts detected: {len(conflicts)}/{len(results)} ({len(conflicts)/len(results)*100:.0%})")
    report.append(f"Physics wins: {len(physics_wins)} ({len(physics_wins)/len(results)*100:.0%})")
    report.append(f"Vision wins: {len(vision_wins)} ({len(vision_wins)/len(results)*100:.0%})")
    report.append("")

    # Detailed results table
    report.append("="*80)
    report.append("DETAILED RESULTS")
    report.append("="*80)
    report.append("")

    for r in results:
        video_num = r['video'].split('_')[-1]
        winner = 'PHYSICS' if 'physics' in r['method'] else 'VISION'
        discarded_str = f"(discarded: {r['discarded']})" if r['discarded'] else ""

        report.append(f"VIDEO #{video_num}:")
        report.append(f"  Winner: {winner}")
        report.append(f"  Final Action: {r['action'].upper()} {discarded_str}")
        report.append(f"  Confidence: {r['confidence']*100:.0%}")
        report.append(f"  Method: {r['method']}")

        if r['scores']:
            physics_score = r['scores'].get('physics', 0)
            vision_score = r['scores'].get('vision', 0)
            report.append(f"  Scores: Physics={physics_score:.2f}, Vision={vision_score:.2f}")

        if r['reasoning']:
            # Truncate long reasoning
            reasoning = r['reasoning']
            if len(reasoning) > 100:
                reasoning = reasoning[:97] + "..."
            report.append(f"  Reasoning: {reasoning}")

        report.append("")

    # Decision patterns
    report.append("="*80)
    report.append("DECISION PATTERNS")
    report.append("="*80)
    report.append("")

    # Group by winner
    report.append("When Physics Won:")
    for r in physics_wins:
        video_num = r['video'].split('_')[-1]
        report.append(f"  Video #{video_num}: {r['action'].upper()} - {r['reasoning'][:60]}...")

    report.append("")
    report.append("When Vision Won:")
    for r in vision_wins:
        video_num = r['video'].split('_')[-1]
        report.append(f"  Video #{video_num}: {r['action'].upper()} - {r['reasoning'][:60]}...")

    # Write report
    report_text = "\n".join(report)
    print(report_text)

    with open('SMART_JUNCTION_REPORT.md', 'w') as f:
        f.write(report_text)

    print("\n💾 Report saved to: SMART_JUNCTION_REPORT.md")

if __name__ == '__main__':
    analyze_smart_junction_results()
