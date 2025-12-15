"""
WEB DASHBOARD GENERATOR
Creates HTML status page that can be viewed from phone via GitHub Pages

Auto-updates and commits to GitHub for remote monitoring
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
import time


class WebDashboardGenerator:
    """Generate web-based dashboard for GitHub Pages"""

    def __init__(self,
                 output_file='docs/index.html',
                 log_file='mining_final_dedup.log',
                 hdf5_dir='data_mine/permanent_data/hdf5'):
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(exist_ok=True)

        self.log_file = Path(log_file)
        self.hdf5_dir = Path(hdf5_dir)
        self.dedup_file = Path('mining_processed_videos.json')

    def get_stats(self):
        """Gather all statistics"""
        stats = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'process': self._get_process_status(),
            'files': self._get_file_stats(),
            'dedup': self._get_dedup_stats(),
            'mining': self._parse_mining_stats()
        }
        return stats

    def _get_process_status(self):
        """Get mining process status"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            lines = [l for l in result.stdout.split('\n')
                    if 'run_overnight_mining.py' in l and 'grep' not in l]

            if lines:
                parts = lines[0].split()
                return {
                    'running': True,
                    'pid': parts[1],
                    'cpu': parts[2],
                    'memory': parts[3]
                }
            return {'running': False}
        except:
            return {'running': False}

    def _get_file_stats(self):
        """Get RGB file statistics"""
        if not self.hdf5_dir.exists():
            return {'count': 0, 'total_size': 0, 'recent': []}

        rgb_files = [f for f in self.hdf5_dir.glob('*.hdf5')
                     if f.stat().st_size > 1_000_000]

        rgb_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        total_size = sum(f.stat().st_size for f in rgb_files)

        recent = []
        for f in rgb_files[:5]:
            stat = f.stat()
            recent.append({
                'name': f.stem,
                'size_mb': round(stat.st_size / 1_000_000, 1),
                'time': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S')
            })

        return {
            'count': len(rgb_files),
            'total_size_mb': round(total_size / 1_000_000, 1),
            'recent': recent
        }

    def _get_dedup_stats(self):
        """Get deduplication statistics"""
        if not self.dedup_file.exists():
            return {'urls_tracked': 0}

        try:
            with open(self.dedup_file, 'r') as f:
                data = json.load(f)
            return {
                'urls_tracked': len(data.get('urls', [])),
                'last_updated': data.get('last_updated', 'unknown')
            }
        except:
            return {'urls_tracked': 0}

    def _parse_mining_stats(self):
        """Parse mining statistics from log"""
        if not self.log_file.exists():
            return {}

        try:
            # Get total log lines
            result = subprocess.run(
                ['wc', '-l', str(self.log_file)],
                capture_output=True,
                text=True
            )
            total_lines = int(result.stdout.strip().split()[0])

            # Parse recent entries
            result = subprocess.run(
                ['tail', '-500', str(self.log_file)],
                capture_output=True,
                text=True
            )

            stats = {
                'accepted': 0,
                'rejected': 0,
                'skipped_dedup': 0,
                'skipped_long': 0,
                'current_query': 'Unknown',
                'log_lines': total_lines
            }

            for line in result.stdout.split('\n'):
                if 'ACCEPTED' in line and 'Score:' in line:
                    stats['accepted'] += 1
                elif 'REJECTED' in line and 'Score:' in line:
                    stats['rejected'] += 1
                elif 'Already processed' in line:
                    stats['skipped_dedup'] += 1
                elif 'too long' in line and 'Skipping' in line:
                    stats['skipped_long'] += 1
                elif line.startswith('🔍 Query'):
                    stats['current_query'] = line.split(':', 1)[1].strip() if ':' in line else 'Unknown'

            total = stats['accepted'] + stats['rejected']
            stats['acceptance_rate'] = round((stats['accepted'] / total * 100), 1) if total > 0 else 0

            return stats
        except:
            return {'log_lines': 0}

    def generate_html(self):
        """Generate HTML dashboard"""
        stats = self.get_stats()

        progress_pct = (stats['files']['count'] / 100) * 100

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Mining Dashboard - {stats['timestamp']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}

        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}

        .status-running {{
            background: #10b981;
            color: white;
        }}

        .status-stopped {{
            background: #ef4444;
            color: white;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .card h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}

        .stat:last-child {{
            border-bottom: none;
        }}

        .stat-label {{
            color: #666;
            font-weight: 500;
        }}

        .stat-value {{
            color: #333;
            font-weight: bold;
        }}

        .progress-bar {{
            width: 100%;
            height: 40px;
            background: #e5e7eb;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
            position: relative;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}

        .file-item {{
            padding: 10px;
            background: #f9fafb;
            border-radius: 8px;
            margin: 8px 0;
            font-size: 0.9em;
        }}

        .file-time {{
            color: #667eea;
            font-weight: bold;
        }}

        .file-size {{
            color: #10b981;
            font-weight: bold;
        }}

        .auto-refresh {{
            text-align: center;
            color: white;
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}

            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Video Intelligence Mining</h1>
            <div class="timestamp">Last Updated: {stats['timestamp']}</div>
            <div class="status-badge {'status-running' if stats['process']['running'] else 'status-stopped'}">
                {'✅ RUNNING' if stats['process']['running'] else '❌ STOPPED'}
                {f" (PID {stats['process']['pid']})" if stats['process']['running'] else ''}
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📊 Gate 1 Progress</h2>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress_pct}%">
                        {stats['files']['count']}/100 ({progress_pct:.1f}%)
                    </div>
                </div>
                <div class="stat">
                    <span class="stat-label">RGB Demos</span>
                    <span class="stat-value">{stats['files']['count']}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Size</span>
                    <span class="stat-value">{stats['files']['total_size_mb']} MB</span>
                </div>
            </div>

            <div class="card">
                <h2>⛏️ Mining Stats</h2>
                <div class="stat">
                    <span class="stat-label">Current Query</span>
                    <span class="stat-value">{stats['mining'].get('current_query', 'Unknown')[:30]}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Accepted</span>
                    <span class="stat-value">{stats['mining'].get('accepted', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Rejected</span>
                    <span class="stat-value">{stats['mining'].get('rejected', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Acceptance Rate</span>
                    <span class="stat-value">{stats['mining'].get('acceptance_rate', 0)}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Skipped (Dedup)</span>
                    <span class="stat-value">{stats['mining'].get('skipped_dedup', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Log Lines</span>
                    <span class="stat-value">{stats['mining'].get('log_lines', 0):,}</span>
                </div>
            </div>

            <div class="card">
                <h2>🔒 Deduplication</h2>
                <div class="stat">
                    <span class="stat-label">URLs Tracked</span>
                    <span class="stat-value">{stats['dedup']['urls_tracked']}</span>
                </div>
                {'<div class="stat"><span class="stat-label">System Health</span><span class="stat-value">✅ Working</span></div>' if stats['process']['running'] else ''}
            </div>
        </div>

        <div class="card">
            <h2>📁 Recent Files</h2>
"""

        for file in stats['files'].get('recent', []):
            html += f"""            <div class="file-item">
                <span class="file-time">⏰ {file['time']}</span> |
                <span class="file-size">{file['size_mb']} MB</span> |
                {file['name'][:60]}
            </div>
"""

        html += """        </div>

        <div class="auto-refresh">
            🔄 Auto-refreshes every 60 seconds
        </div>
    </div>
</body>
</html>
"""

        return html

    def save(self):
        """Generate and save HTML"""
        html = self.generate_html()
        with open(self.output_file, 'w') as f:
            f.write(html)
        return self.output_file


def main():
    """Generate web dashboard"""
    generator = WebDashboardGenerator()
    output_file = generator.save()
    print(f"✅ Web dashboard generated: {output_file}")
    print(f"   View locally: open {output_file}")


if __name__ == '__main__':
    main()
