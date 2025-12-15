"""
IMAGE DOWNLOADER
Download images from multiple sources for robot training data mining

Sources:
- Unsplash (free, high quality, API available)
- Pexels (free, API available)
- Pixabay (free, API available)

Usage:
    downloader = ImageDownloader(output_dir='images')
    images = downloader.search_and_download('person reaching', max_images=50)
"""

import requests
import json
from pathlib import Path
import time
from datetime import datetime


class ImageDownloader:
    """
    Download images from free stock photo APIs

    APIs used (all free):
    1. Unsplash - https://unsplash.com/developers
    2. Pexels - https://www.pexels.com/api/
    3. Pixabay - https://pixabay.com/api/docs/
    """

    def __init__(self, output_dir='images', source='unsplash'):
        """
        Args:
            output_dir: Directory to save images
            source: Image source ('unsplash', 'pexels', 'pixabay', 'all')
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.source = source

        # API keys (set via environment variables or use demo mode)
        import os
        self.unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY', 'DEMO')
        self.pexels_key = os.getenv('PEXELS_API_KEY', 'DEMO')
        self.pixabay_key = os.getenv('PIXABAY_API_KEY', 'DEMO')

        self.stats = {
            'images_downloaded': 0,
            'sources_used': [],
            'queries': []
        }

    def search_unsplash(self, query, max_images=30):
        """
        Search and download from Unsplash

        Note: Unsplash allows non-commercial use without API key (limited)
        For production, get free API key at: https://unsplash.com/developers
        """
        print(f"🔍 Searching Unsplash for: {query}")

        # Use Unsplash Source API (no key needed for basic use)
        # Format: https://source.unsplash.com/1600x900/?{query}
        # For search API (requires key), use: https://api.unsplash.com/search/photos

        downloaded = []

        for i in range(max_images):
            try:
                # Unsplash Source API (random image for query)
                url = f"https://source.unsplash.com/1600x900/?{query}&sig={i}"

                print(f"   [{i+1}/{max_images}] Downloading...")

                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    # Generate filename
                    timestamp = int(time.time() * 1000)
                    filename = f"unsplash_{query.replace(' ', '_')}_{timestamp}_{i}.jpg"
                    filepath = self.output_dir / filename

                    # Save image
                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded.append(str(filepath))
                    print(f"   ✅ {filename}")

                    # Save metadata
                    metadata = {
                        'source': 'unsplash',
                        'query': query,
                        'downloaded_at': datetime.now().isoformat(),
                        'url': url,
                        'filename': filename
                    }

                    meta_path = self.output_dir / f"{filename}.json"
                    with open(meta_path, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    # Rate limiting
                    time.sleep(1)

                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")

            except Exception as e:
                print(f"   ❌ Error: {e}")

        return downloaded

    def search_pexels(self, query, max_images=30):
        """
        Search and download from Pexels

        Get free API key at: https://www.pexels.com/api/
        """
        if self.pexels_key == 'DEMO':
            print("⚠️  Pexels requires API key. Get free key at: https://www.pexels.com/api/")
            print("   Set: export PEXELS_API_KEY='your_key'")
            return []

        print(f"🔍 Searching Pexels for: {query}")

        headers = {'Authorization': self.pexels_key}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page={max_images}"

        downloaded = []

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                for i, photo in enumerate(data.get('photos', [])):
                    try:
                        # Download medium size image
                        img_url = photo['src']['medium']
                        img_response = requests.get(img_url, timeout=10)

                        if img_response.status_code == 200:
                            filename = f"pexels_{query.replace(' ', '_')}_{photo['id']}.jpg"
                            filepath = self.output_dir / filename

                            with open(filepath, 'wb') as f:
                                f.write(img_response.content)

                            downloaded.append(str(filepath))
                            print(f"   [{i+1}/{len(data['photos'])}] ✅ {filename}")

                            # Save metadata
                            metadata = {
                                'source': 'pexels',
                                'query': query,
                                'photo_id': photo['id'],
                                'photographer': photo['photographer'],
                                'url': photo['url'],
                                'downloaded_at': datetime.now().isoformat()
                            }

                            meta_path = self.output_dir / f"{filename}.json"
                            with open(meta_path, 'w') as f:
                                json.dump(metadata, f, indent=2)

                            time.sleep(0.5)

                    except Exception as e:
                        print(f"   ❌ Error downloading {photo['id']}: {e}")

        except Exception as e:
            print(f"❌ Pexels API error: {e}")

        return downloaded

    def search_and_download(self, query, max_images=30):
        """
        Search and download images

        Args:
            query: Search query (e.g., 'person reaching', 'hand grabbing')
            max_images: Maximum images to download

        Returns:
            List of downloaded image paths
        """
        print("="*70)
        print("IMAGE DOWNLOADER")
        print("="*70)
        print(f"Query: {query}")
        print(f"Max images: {max_images}")
        print(f"Source: {self.source}")
        print()

        downloaded = []

        if self.source == 'unsplash' or self.source == 'all':
            downloaded.extend(self.search_unsplash(query, max_images))

        if self.source == 'pexels' or self.source == 'all':
            downloaded.extend(self.search_pexels(query, max_images))

        print()
        print("="*70)
        print(f"✅ Downloaded {len(downloaded)} images")
        print("="*70)
        print()

        self.stats['images_downloaded'] += len(downloaded)
        self.stats['queries'].append(query)

        return downloaded


def main():
    """Test image downloader"""
    import argparse

    parser = argparse.ArgumentParser(description='Download images for robot training')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-images', type=int, default=30,
                       help='Maximum images to download')
    parser.add_argument('--source', default='unsplash',
                       choices=['unsplash', 'pexels', 'all'],
                       help='Image source')
    parser.add_argument('--output', default='images',
                       help='Output directory')

    args = parser.parse_args()

    downloader = ImageDownloader(output_dir=args.output, source=args.source)
    downloaded = downloader.search_and_download(args.query, args.max_images)

    print(f"\n✅ Downloaded {len(downloaded)} images to {args.output}/")


if __name__ == '__main__':
    main()
