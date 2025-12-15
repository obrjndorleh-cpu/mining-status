"""
YOUTUBE PIPELINE TESTER

Downloads diverse YouTube videos and tests the complete pipeline.
Validates system performance on real-world data.
"""

import json
from pathlib import Path
from youtube_downloader import YouTubeDownloader
import subprocess
import sys


def load_task_queries(json_file='robot_task_queries.json'):
    """Load curated task queries from JSON"""
    with open(json_file, 'r') as f:
        return json.load(f)


def test_pipeline_on_youtube_videos(num_tasks=3, videos_per_task=1):
    """
    Download YouTube videos for diverse tasks and test pipeline

    Args:
        num_tasks: Number of different tasks to test
        videos_per_task: Number of videos per task
    """
    print("="*70)
    print("YOUTUBE PIPELINE TESTING")
    print("="*70)
    print(f"Tasks to test: {num_tasks}")
    print(f"Videos per task: {videos_per_task}")
    print()

    # Load task queries
    task_data = load_task_queries()

    # Flatten all tasks
    all_tasks = []
    for category, tasks in task_data.items():
        for task in tasks:
            task['category'] = category
            all_tasks.append(task)

    print(f"Available tasks: {len(all_tasks)}")
    print()

    # Select diverse tasks
    selected_tasks = all_tasks[:num_tasks]

    downloader = YouTubeDownloader(output_dir='youtube_test_videos')
    results = []

    for i, task_info in enumerate(selected_tasks, 1):
        task_name = task_info['task']
        category = task_info['category']
        queries = task_info['queries']
        expected_actions = task_info['expected_actions']

        print("="*70)
        print(f"TASK {i}/{num_tasks}: {task_name}")
        print(f"Category: {category}")
        print(f"Expected actions: {', '.join(expected_actions)}")
        print("="*70)
        print()

        # Try each query until we get videos
        downloaded_videos = []
        for query in queries:
            if len(downloaded_videos) >= videos_per_task:
                break

            print(f"🔍 Query: {query}")
            videos = downloader.search_and_download(
                query,
                max_results=videos_per_task,
                max_duration=20  # Short clips for faster testing
            )
            downloaded_videos.extend(videos)

        if not downloaded_videos:
            print(f"⚠️  No videos downloaded for {task_name}")
            print()
            continue

        # Test pipeline on each video
        for video_path in downloaded_videos:
            print()
            print("="*70)
            print(f"TESTING PIPELINE: {video_path.name}")
            print("="*70)

            # Run unified pipeline with dual-stream
            output_dir = f"youtube_test_output/{task_name}"
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            cmd = [
                'python', 'unified_pipeline.py',
                str(video_path),
                output_dir,
                '--enable-vision'
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout
                )

                # Extract key results
                output = result.stdout

                # Look for reconciliation result
                detected_action = "unknown"
                method = "unknown"
                confidence = 0.0

                for line in output.split('\n'):
                    if 'Reconciliation complete:' in line:
                        detected_action = line.split(':')[-1].strip()
                    elif 'Method:' in line:
                        method = line.split(':')[-1].strip()
                    elif 'Confidence:' in line:
                        try:
                            confidence = float(line.split(':')[-1].strip().rstrip('%')) / 100
                        except:
                            pass

                # Check if detected action matches expected
                match = detected_action.lower() in [a.lower() for a in expected_actions]

                result_entry = {
                    'task': task_name,
                    'category': category,
                    'video': video_path.name,
                    'expected': expected_actions,
                    'detected': detected_action,
                    'method': method,
                    'confidence': confidence,
                    'match': match,
                    'success': result.returncode == 0
                }

                results.append(result_entry)

                # Print result
                status = "✅" if match else "❌"
                print()
                print(f"{status} Result:")
                print(f"   Expected: {', '.join(expected_actions)}")
                print(f"   Detected: {detected_action}")
                print(f"   Method: {method}")
                print(f"   Confidence: {confidence:.0%}")
                print(f"   Match: {match}")
                print()

            except subprocess.TimeoutExpired:
                print(f"⏱️  Pipeline timeout for {video_path.name}")
                results.append({
                    'task': task_name,
                    'video': video_path.name,
                    'success': False,
                    'error': 'timeout'
                })
            except Exception as e:
                print(f"❌ Pipeline error: {e}")
                results.append({
                    'task': task_name,
                    'video': video_path.name,
                    'success': False,
                    'error': str(e)
                })

        print()

    # Summary report
    print("="*70)
    print("YOUTUBE PIPELINE TEST SUMMARY")
    print("="*70)
    print()

    successful = [r for r in results if r.get('success', False)]
    matched = [r for r in results if r.get('match', False)]

    print(f"Total videos tested: {len(results)}")
    print(f"Successful processing: {len(successful)} ({len(successful)/len(results)*100:.0%})")
    print(f"Correct detections: {len(matched)} ({len(matched)/len(results)*100:.0%})")
    print()

    # Breakdown by task
    print("Results by task:")
    for task_info in selected_tasks:
        task_name = task_info['task']
        task_results = [r for r in results if r.get('task') == task_name]
        task_matched = [r for r in task_results if r.get('match', False)]

        if task_results:
            accuracy = len(task_matched) / len(task_results) * 100
            print(f"  {task_name}: {len(task_matched)}/{len(task_results)} ({accuracy:.0%})")

    print()

    # Save results
    results_file = 'youtube_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'summary': {
                'total_videos': len(results),
                'successful': len(successful),
                'matched': len(matched),
                'accuracy': len(matched) / len(results) if results else 0
            },
            'results': results
        }, f, indent=2)

    print(f"💾 Saved results to: {results_file}")
    print()

    return results


def quick_test(query="opening refrigerator door first person", max_videos=1):
    """
    Quick test with a single search query

    Args:
        query: Search query
        max_videos: Number of videos to download and test
    """
    print("="*70)
    print("QUICK YOUTUBE PIPELINE TEST")
    print("="*70)
    print(f"Query: {query}")
    print(f"Videos: {max_videos}")
    print()

    downloader = YouTubeDownloader(output_dir='youtube_test_videos')

    # Download videos
    videos = downloader.search_and_download(query, max_results=max_videos, max_duration=15)

    if not videos:
        print("❌ No videos downloaded")
        return

    # Test on first video
    video_path = videos[0]
    print()
    print("="*70)
    print(f"TESTING: {video_path.name}")
    print("="*70)

    cmd = [
        'python', 'unified_pipeline.py',
        str(video_path),
        'youtube_quick_test',
        '--enable-vision'
    ]

    subprocess.run(cmd)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test pipeline on YouTube videos')
    parser.add_argument('--quick', action='store_true', help='Quick test with one video')
    parser.add_argument('--query', default='opening refrigerator door first person', help='Search query for quick test')
    parser.add_argument('--tasks', type=int, default=3, help='Number of tasks to test')
    parser.add_argument('--videos-per-task', type=int, default=1, help='Videos per task')

    args = parser.parse_args()

    if args.quick:
        quick_test(query=args.query)
    else:
        test_pipeline_on_youtube_videos(
            num_tasks=args.tasks,
            videos_per_task=args.videos_per_task
        )
