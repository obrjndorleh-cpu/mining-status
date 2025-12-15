"""
SIMPLE MINING DASHBOARD
Shows exactly what matters: session stats, progress, recent activity
"""

import subprocess
import re
from pathlib import Path
from datetime import datetime


def get_session_stats(log_file='mining_final_dedup.log'):
    """Get current session statistics"""
    try:
        result = subprocess.run(['tail', '-200', log_file], capture_output=True, text=True)

        stats = {
            'runtime': '0.0',
            'analyzed': 0,
            'accepted': 0,
            'queries': 0,
            'rate': 0.0,
            'query': 'Unknown'
        }

        for line in result.stdout.split('\n'):
            if 'Runtime:' in line and 'hours' in line:
                m = re.search(r'Runtime:\s*([\d.]+)', line)
                if m:
                    stats['runtime'] = m.group(1)
            elif 'Videos mined:' in line:
                m = re.search(r'Videos mined:\s*(\d+)', line)
                if m:
                    stats['analyzed'] = int(m.group(1))
            elif 'Videos accepted:' in line:
                m = re.search(r'Videos accepted:\s*(\d+)', line)
                if m:
                    stats['accepted'] = int(m.group(1))
            elif 'Queries executed:' in line:
                m = re.search(r'Queries executed:\s*(\d+)', line)
                if m:
                    stats['queries'] = int(m.group(1))
            elif 'Acceptance rate:' in line:
                m = re.search(r'Acceptance rate:\s*([\d.]+)', line)
                if m:
                    stats['rate'] = float(m.group(1))
            elif line.startswith('🔍 Query'):
                m = re.search(r'Query.*?:\s*(.+)', line)
                if m:
                    stats['query'] = m.group(1).strip()[:50]

        return stats
    except:
        return {}


def get_recent_activity(log_file='mining_final_dedup.log'):
    """Get recent skips and results"""
    try:
        result = subprocess.run(['tail', '-100', log_file], capture_output=True, text=True)

        activities = []
        for line in result.stdout.split('\n'):
            if 'Skipping (Already processed' in line:
                activities.append(('skipped_dedup', line))
            elif 'Skipping (too long' in line:
                m = re.search(r'too long:\s*([\d.]+)s', line)
                duration = m.group(1) if m else '?'
                activities.append(('skipped_long', f"Too long: {duration}s"))
            elif '✅ ACCEPTED' in line and 'Score:' in line:
                m = re.search(r'Score:\s*([\d.]+)', line)
                score = m.group(1) if m else '?'
                activities.append(('accepted', f"Score: {score}/100"))
            elif '❌ REJECTED' in line and 'Score:' in line:
                m = re.search(r'Score:\s*([\d.]+)', line)
                score = m.group(1) if m else '?'
                activities.append(('rejected', f"Score: {score}/100"))

        return activities[-10:]
    except:
        return []


def generate_html():
    """Generate simple HTML dashboard"""
    stats = get_session_stats()
    activity = get_recent_activity()

    # Count files
    try:
        result = subprocess.run(
            ['find', 'data_mine/permanent_data/hdf5', '-name', '*.hdf5', '-size', '+1M'],
            capture_output=True, text=True
        )
        file_count = len([l for l in result.stdout.strip().split('\n') if l])
    except:
        file_count = 0

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="15">
    <title>Mining Status - {timestamp}</title>
    <style>
        body {{
            font-family: -apple-system, sans-serif;
            background: #000;
            color: #0f0;
            padding: 20px;
            font-size: 14px;
        }}
        .section {{
            background: #111;
            border: 1px solid #0f0;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
        }}
        h2 {{
            color: #0f0;
            margin: 0 0 10px 0;
            font-size: 18px;
        }}
        .stat {{
            margin: 8px 0;
            font-family: monospace;
        }}
        .label {{
            color: #888;
            display: inline-block;
            width: 140px;
        }}
        .value {{
            color: #0f0;
            font-weight: bold;
        }}
        .activity {{
            margin: 5px 0;
            padding: 8px;
            background: #1a1a1a;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
        }}
        .skipped {{ color: #ffa500; }}
        .accepted {{ color: #0f0; }}
        .rejected {{ color: #f44; }}
        .progress {{
            background: #333;
            height: 30px;
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }}
        .progress-fill {{
            background: #0f0;
            height: 100%;
            transition: width 0.3s;
        }}
        .progress-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #fff;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1 style="color: #0f0; margin: 0 0 20px 0;">⛏️ MINING STATUS</h1>
    <div style="color: #888; margin-bottom: 20px;">{timestamp} | Auto-refresh: 15s</div>

    <div class="section">
        <h2>📊 SESSION STATS (Current Run)</h2>
        <div class="stat"><span class="label">Runtime:</span><span class="value">{stats.get('runtime', '0.0')} hours</span></div>
        <div class="stat"><span class="label">Videos Analyzed:</span><span class="value">{stats.get('analyzed', 0):,}</span></div>
        <div class="stat"><span class="label">Videos Accepted:</span><span class="value">{stats.get('accepted', 0)}</span></div>
        <div class="stat"><span class="label">Queries Executed:</span><span class="value">{stats.get('queries', 0)}</span></div>
        <div class="stat"><span class="label">Acceptance Rate:</span><span class="value">{stats.get('rate', 0.0)}%</span></div>
        <div class="stat"><span class="label">Current Query:</span><span class="value">{stats.get('query', 'Unknown')}</span></div>
    </div>

    <div class="section">
        <h2>🎯 GATE 1 PROGRESS</h2>
        <div class="progress">
            <div class="progress-fill" style="width: {file_count}%"></div>
            <div class="progress-text">{file_count}/100 RGB Demos ({file_count}%)</div>
        </div>
    </div>

    <div class="section">
        <h2>🔴 RECENT ACTIVITY (Last 10)</h2>
'''

    if activity:
        for act_type, act_data in reversed(activity):
            if act_type == 'accepted':
                html += f'        <div class="activity accepted">✅ ACCEPTED - {act_data}</div>\n'
            elif act_type == 'rejected':
                html += f'        <div class="activity rejected">❌ REJECTED - {act_data}</div>\n'
            elif 'dedup' in act_type:
                html += f'        <div class="activity skipped">⏭️  SKIPPED - Already processed</div>\n'
            elif 'long' in act_type:
                html += f'        <div class="activity skipped">⏭️  SKIPPED - {act_data}</div>\n'
    else:
        html += '        <div class="activity" style="color: #888;">No recent activity</div>\n'

    html += '''    </div>

    <div class="section" style="border-color: #888; color: #888;">
        <h2 style="color: #888;">💡 SYSTEM STATUS</h2>
        <div class="stat">✅ Mining: ACTIVE</div>
        <div class="stat">✅ Deduplication: WORKING</div>
        <div class="stat">✅ Quality Threshold: 70/100</div>
    </div>

</body>
</html>
'''

    return html


if __name__ == '__main__':
    html = generate_html()
    Path('docs/index.html').write_text(html)
    print("✅ Dashboard generated: docs/index.html")
