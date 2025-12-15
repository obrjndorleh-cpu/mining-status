"""
CLOUD DATA MINING SETUP

Upload mined data to MongoDB Atlas (cloud) automatically.
Your computer mines → Uploads → Deletes local → Frees space → Mines more!

Benefits:
- Unlimited storage (MongoDB Atlas free tier = 512MB, paid = unlimited)
- Access from anywhere (phone, laptop, anywhere)
- Computer always has free space
- Data safe in cloud (backup + redundancy)
- Query via MCP tools
"""

from pymongo import MongoClient
from datetime import datetime
import json
from pathlib import Path
import os


class CloudMiningSetup:
    """
    Setup MongoDB Atlas connection for cloud data mining
    """

    def __init__(self, mongo_uri=None):
        """
        Args:
            mongo_uri: MongoDB Atlas connection string
                      Format: mongodb+srv://<username>:<password>@cluster.mongodb.net/

                      Get free MongoDB Atlas:
                      1. Go to https://cloud.mongodb.com
                      2. Sign up (free tier = 512MB)
                      3. Create cluster
                      4. Get connection string
        """
        # Try environment variable first
        if mongo_uri is None:
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

        self.mongo_uri = mongo_uri
        self.is_cloud = 'mongodb+srv' in mongo_uri or 'cloud.mongodb.com' in mongo_uri

        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client['data_mining_empire']

            # Test connection
            self.client.admin.command('ping')

            print(f"✅ Connected to MongoDB: {'CLOUD ☁️' if self.is_cloud else 'LOCAL'}")

            # Collections for different data types
            self.robot_data = self.db['robot_training_data']
            self.image_data = self.db['image_datasets']
            self.video_metadata = self.db['video_metadata']
            self.mining_stats = self.db['mining_statistics']

        except Exception as e:
            print(f"⚠️  MongoDB connection failed: {e}")
            print("\n💡 TO USE CLOUD STORAGE:")
            print("1. Sign up at https://cloud.mongodb.com (FREE)")
            print("2. Create cluster")
            print("3. Get connection string")
            print("4. Set environment variable:")
            print("   export MONGODB_URI='mongodb+srv://username:password@cluster.mongodb.net/'")
            print("\nOR run locally: mongodb://localhost:27017/")
            self.client = None

    def upload_robot_sample(self, hdf5_path, json_path=None, video_metadata=None):
        """
        Upload robot training sample to cloud

        Args:
            hdf5_path: Path to HDF5 file (will be uploaded)
            json_path: Path to JSON metadata (optional)
            video_metadata: Video source metadata (optional)

        Returns:
            document_id: MongoDB document ID
        """
        if not self.client:
            return None

        hdf5_path = Path(hdf5_path)

        # Read HDF5 file
        with open(hdf5_path, 'rb') as f:
            hdf5_data = f.read()

        # Create document
        document = {
            'type': 'robot_training',
            'filename': hdf5_path.name,
            'hdf5_data': hdf5_data,  # Store binary data
            'size_bytes': len(hdf5_data),
            'uploaded_at': datetime.now(),
            'source': 'youtube_mining'
        }

        # Add JSON metadata if provided
        if json_path and Path(json_path).exists():
            with open(json_path, 'r') as f:
                document['metadata'] = json.load(f)

        # Add video metadata if provided
        if video_metadata:
            document['video_metadata'] = video_metadata

        # Upload to cloud
        result = self.robot_data.insert_one(document)

        print(f"☁️  Uploaded to cloud: {hdf5_path.name} ({len(hdf5_data)/1024:.1f} KB)")

        return result.inserted_id

    def upload_mining_batch(self, data_dir='data_mine/permanent_data'):
        """
        Upload all mined data to cloud in batch

        Args:
            data_dir: Directory containing mined data
        """
        if not self.client:
            print("❌ Not connected to MongoDB")
            return

        data_dir = Path(data_dir)
        hdf5_dir = data_dir / 'hdf5'
        json_dir = data_dir / 'json'

        if not hdf5_dir.exists():
            print(f"⚠️  No data found in {hdf5_dir}")
            return

        hdf5_files = list(hdf5_dir.glob('*.hdf5'))

        print("="*70)
        print("☁️  UPLOADING TO CLOUD")
        print("="*70)
        print(f"Files to upload: {len(hdf5_files)}")
        print()

        uploaded = 0
        total_size = 0

        for hdf5_file in hdf5_files:
            # Find corresponding JSON
            json_file = json_dir / f"{hdf5_file.stem}_reconciled.json"

            try:
                doc_id = self.upload_robot_sample(
                    hdf5_file,
                    json_path=json_file if json_file.exists() else None
                )

                if doc_id:
                    uploaded += 1
                    total_size += hdf5_file.stat().st_size

            except Exception as e:
                print(f"❌ Failed to upload {hdf5_file.name}: {e}")

        print()
        print("="*70)
        print(f"✅ Uploaded {uploaded}/{len(hdf5_files)} files")
        print(f"📦 Total size: {total_size/1024/1024:.2f} MB")
        print("="*70)

    def get_mining_statistics(self):
        """Get statistics from cloud database"""
        if not self.client:
            return {}

        stats = {
            'robot_samples': self.robot_data.count_documents({}),
            'total_size_mb': 0,
            'storage_location': 'CLOUD ☁️' if self.is_cloud else 'LOCAL',
        }

        # Calculate total size
        pipeline = [
            {'$group': {
                '_id': None,
                'total_size': {'$sum': '$size_bytes'}
            }}
        ]
        result = list(self.robot_data.aggregate(pipeline))
        if result:
            stats['total_size_mb'] = result[0]['total_size'] / 1024 / 1024

        return stats

    def print_status(self):
        """Print cloud mining status"""
        if not self.client:
            print("❌ Not connected to MongoDB")
            return

        stats = self.get_mining_statistics()

        print()
        print("="*70)
        print(f"☁️  CLOUD MINING STATUS")
        print("="*70)
        print(f"Storage: {stats['storage_location']}")
        print(f"Robot training samples: {stats['robot_samples']}")
        print(f"Total data stored: {stats['total_size_mb']:.2f} MB")
        print()

        if self.is_cloud:
            print("💡 ACCESS FROM ANYWHERE:")
            print("   - MongoDB Compass (GUI)")
            print("   - MCP tools (query from Claude)")
            print("   - MongoDB mobile app")
            print("   - Any device with internet")

        print("="*70)
        print()


def main():
    """
    Setup cloud mining
    """
    import argparse

    parser = argparse.ArgumentParser(description='Cloud data mining setup')
    parser.add_argument('--upload', action='store_true',
                       help='Upload all mined data to cloud')
    parser.add_argument('--status', action='store_true',
                       help='Show cloud mining status')
    parser.add_argument('--mongo-uri',
                       help='MongoDB connection URI (or set MONGODB_URI env var)')

    args = parser.parse_args()

    # Create cloud setup
    cloud = CloudMiningSetup(mongo_uri=args.mongo_uri)

    if args.upload:
        cloud.upload_mining_batch()

    if args.status or not (args.upload):
        cloud.print_status()


if __name__ == '__main__':
    main()
