"""
YOUTUBE VIDEO DOWNLOADER

Downloads videos from YouTube for pipeline development and testing.
Handles quality selection, clipping, and metadata extraction.
"""

import yt_dlp
import os
import json
import time
from pathlib import Path


class YouTubeDownloader:
    """
    Download and prepare YouTube videos for robot data pipeline
    """

    def __init__(self, output_dir='youtube_videos', use_rate_limiting=True, use_deduplication=True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize rate limiter
        self.use_rate_limiting = use_rate_limiting
        if use_rate_limiting:
            from rate_limit_manager import RateLimitManager
            self.rate_limiter = RateLimitManager()
        else:
            self.rate_limiter = None

        # Initialize deduplication manager
        self.use_deduplication = use_deduplication
        if use_deduplication:
            from deduplication_manager import DeduplicationManager
            self.dedup = DeduplicationManager()
        else:
            self.dedup = None

    def download(self, url, start_time=None, end_time=None, max_duration=30):
        """
        Download YouTube video

        Args:
            url: YouTube video URL or ID
            start_time: Start time in seconds (optional, for clipping)
            end_time: End time in seconds (optional, for clipping)
            max_duration: Maximum video duration to download (default: 30s)

        Returns:
            Path to downloaded video file
        """
        print("="*70)
        print("YOUTUBE VIDEO DOWNLOADER")
        print("="*70)
        print(f"URL: {url}")
        if start_time is not None:
            print(f"Clip: {start_time}s - {end_time}s")
        print()

        # Check rate limits
        if self.rate_limiter:
            can_download, reason, wait_time = self.rate_limiter.can_download()

            if not can_download:
                print(f"⚠️  RATE LIMIT: {reason}")
                if wait_time > 0:
                    print(f"   Waiting {wait_time}s ({wait_time/60:.1f} minutes)...")
                    time.sleep(wait_time)
                else:
                    print(f"   ERROR: Cannot proceed - {reason}")
                    return None

            # Recommended delay before this download
            delay = self.rate_limiter.get_recommended_delay()
            if delay > self.rate_limiter.config['min_delay_seconds']:
                print(f"⏱️  Rate limiting: Waiting {delay}s before download...")
                time.sleep(delay)

        # Configure yt-dlp options
        # DATA-DRIVEN FIX: YouTube sometimes restricts video formats
        # Use format filter that explicitly requires BOTH video AND audio
        ydl_opts = {
            'format': 'bv*+ba/b',  # Best video+audio OR best single file with both
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'merge_output_format': 'mp4',  # Merge to mp4
            # Bypass restrictions
            'cookiesfrombrowser': ('chrome',),  # Use browser cookies if available
            'extractor_args': {'youtube': {'player_client': ['android']}},  # Use Android client
        }

        # Add download sections if clipping
        if start_time is not None and end_time is not None:
            ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(
                None, [(start_time, end_time)]
            )
            ydl_opts['force_keyframes_at_cuts'] = True

        try:
            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("📥 Downloading video...")
                info = ydl.extract_info(url, download=True)

                # Get output filename
                filename = ydl.prepare_filename(info)
                video_path = Path(filename)

                print(f"✅ Downloaded: {video_path.name}")
                print(f"   Duration: {info.get('duration', 'unknown')}s")
                print(f"   Resolution: {info.get('width', '?')}x{info.get('height', '?')}")
                print(f"   FPS: {info.get('fps', '?')}")
                print()

                # Save metadata
                metadata = {
                    'title': info.get('title'),
                    'url': url,
                    'duration': info.get('duration'),
                    'resolution': f"{info.get('width')}x{info.get('height')}",
                    'fps': info.get('fps'),
                    'upload_date': info.get('upload_date'),
                    'uploader': info.get('uploader'),
                    'description': info.get('description', '')[:500],  # First 500 chars
                    'clip': {
                        'start': start_time,
                        'end': end_time
                    } if start_time is not None else None
                }

                metadata_path = video_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                print(f"💾 Saved metadata: {metadata_path.name}")
                print()

                # Record successful download
                if self.rate_limiter:
                    self.rate_limiter.record_download(success=True)

                return video_path

        except Exception as e:
            print(f"❌ Error downloading video: {e}")

            # Record failed download
            if self.rate_limiter:
                # Try to extract error code
                error_code = None
                error_str = str(e)
                if '403' in error_str:
                    error_code = 403
                elif '429' in error_str:
                    error_code = 429
                self.rate_limiter.record_download(success=False, error_code=error_code)

            return None

    def download_playlist(self, playlist_url, max_videos=5, max_duration_per_video=30):
        """
        Download multiple videos from a playlist

        Args:
            playlist_url: YouTube playlist URL
            max_videos: Maximum number of videos to download
            max_duration_per_video: Skip videos longer than this (seconds)

        Returns:
            List of downloaded video paths
        """
        print("="*70)
        print("YOUTUBE PLAYLIST DOWNLOADER")
        print("="*70)
        print(f"Playlist: {playlist_url}")
        print(f"Max videos: {max_videos}")
        print()

        ydl_opts = {
            'format': 'best[ext=mp4][height<=720]',
            'outtmpl': str(self.output_dir / '%(playlist_index)s_%(title)s.%(ext)s'),
            'quiet': True,
            'extract_flat': True,  # Just get metadata first
            'playlistend': max_videos,
        }

        downloaded_videos = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get playlist info
                print("📋 Fetching playlist info...")
                playlist_info = ydl.extract_info(playlist_url, download=False)

                videos = playlist_info['entries'][:max_videos]
                print(f"Found {len(videos)} videos")
                print()

                # Download each video
                for i, video in enumerate(videos, 1):
                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                    print(f"[{i}/{len(videos)}] {video.get('title', 'Unknown')}")

                    # Check duration
                    if video.get('duration', 0) > max_duration_per_video:
                        print(f"   ⏭️  Skipping (too long: {video['duration']}s)")
                        print()
                        continue

                    video_path = self.download(video_url)
                    if video_path:
                        downloaded_videos.append(video_path)

                print("="*70)
                print(f"✅ Downloaded {len(downloaded_videos)} videos")
                print("="*70)

                return downloaded_videos

        except Exception as e:
            print(f"❌ Error downloading playlist: {e}")
            return downloaded_videos

    def search_and_download(self, query, max_results=3, max_duration=30):
        """
        Search YouTube and download top results

        Args:
            query: Search query (e.g., "opening refrigerator door")
            max_results: Number of videos to download
            max_duration: Maximum video duration (seconds)

        Returns:
            List of downloaded video paths
        """
        print("="*70)
        print("YOUTUBE SEARCH & DOWNLOAD")
        print("="*70)
        print(f"Query: {query}")
        print(f"Max results: {max_results}")
        print()

        ydl_opts = {
            'format': 'best[ext=mp4][height<=720]',
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
        }

        search_query = f"ytsearch{max_results}:{query}"
        downloaded_videos = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"🔍 Searching for: {query}")
                search_results = ydl.extract_info(search_query, download=False)

                videos = search_results['entries']
                print(f"Found {len(videos)} videos")
                print()

                for i, video in enumerate(videos, 1):
                    if not video:
                        continue

                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                    video_title = video.get('title', 'Unknown')
                    print(f"[{i}/{len(videos)}] {video_title}")

                    # Check deduplication first
                    if self.dedup:
                        should_process, reason = self.dedup.should_process(video_url, video_title)
                        if not should_process:
                            print(f"   ⏭️  Skipping ({reason})")
                            print()
                            continue

                    # Check duration
                    if video.get('duration', 0) > max_duration:
                        print(f"   ⏭️  Skipping (too long: {video['duration']}s)")
                        print()
                        continue

                    video_path = self.download(video_url)
                    if video_path:
                        downloaded_videos.append(video_path)
                        # Mark as processed after successful download
                        if self.dedup:
                            self.dedup.mark_processed(video_url, video_title)

                print("="*70)
                print(f"✅ Downloaded {len(downloaded_videos)} videos")
                print("="*70)

                return downloaded_videos

        except Exception as e:
            print(f"❌ Error searching/downloading: {e}")
            return downloaded_videos


def main():
    """
    Example usage and testing
    """
    import argparse

    parser = argparse.ArgumentParser(description='Download YouTube videos for robot data pipeline')
    parser.add_argument('url', nargs='?', help='YouTube URL or search query')
    parser.add_argument('--search', action='store_true', help='Treat URL as search query')
    parser.add_argument('--playlist', action='store_true', help='Download playlist')
    parser.add_argument('--start', type=int, help='Clip start time (seconds)')
    parser.add_argument('--end', type=int, help='Clip end time (seconds)')
    parser.add_argument('--max-results', type=int, default=3, help='Max search results')
    parser.add_argument('--max-duration', type=int, default=30, help='Max video duration (seconds)')
    parser.add_argument('--output', default='youtube_videos', help='Output directory')

    args = parser.parse_args()

    downloader = YouTubeDownloader(output_dir=args.output)

    if args.search:
        # Search and download
        videos = downloader.search_and_download(
            args.url,
            max_results=args.max_results,
            max_duration=args.max_duration
        )
    elif args.playlist:
        # Download playlist
        videos = downloader.download_playlist(
            args.url,
            max_videos=args.max_results,
            max_duration_per_video=args.max_duration
        )
    else:
        # Download single video
        video = downloader.download(args.url, start_time=args.start, end_time=args.end)
        videos = [video] if video else []

    print()
    print("📁 Downloaded videos:")
    for video in videos:
        print(f"   - {video}")


if __name__ == '__main__':
    main()
