"""
AUTO-PUSH STATUS TO GITHUB
Continuously updates web dashboard and pushes to GitHub
Allows phone monitoring via GitHub Pages
"""

import time
import subprocess
from pathlib import Path
from web_dashboard_generator import WebDashboardGenerator


def git_commit_and_push(message="Update mining status"):
    """Commit and push changes to GitHub"""
    try:
        # Add docs folder
        subprocess.run(['git', 'add', 'docs/'], check=True)

        # Check if there are changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            print("   No changes to commit")
            return True

        # Commit
        subprocess.run(
            ['git', 'commit', '-m', message],
            check=True,
            capture_output=True
        )

        # Push
        subprocess.run(['git', 'push'], check=True, capture_output=True)

        print(f"   ✅ Pushed to GitHub: {message}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Git error: {e}")
        return False


def main():
    """Main loop - update and push every 2 minutes"""
    generator = WebDashboardGenerator()

    print("=" * 70)
    print("🚀 AUTO-PUSH STATUS TO GITHUB")
    print("=" * 70)
    print("This will update your GitHub Pages dashboard every 2 minutes")
    print("View from phone: https://YOUR_USERNAME.github.io/YOUR_REPO/")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n[{iteration}] Updating dashboard...")

            # Generate HTML
            output_file = generator.save()
            print(f"   ✅ Generated: {output_file}")

            # Push to GitHub
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            git_commit_and_push(f"Update mining status - {timestamp}")

            print(f"   ⏰ Next update in 2 minutes...")
            time.sleep(120)  # 2 minutes

    except KeyboardInterrupt:
        print("\n\n👋 Auto-push stopped")


if __name__ == '__main__':
    main()
