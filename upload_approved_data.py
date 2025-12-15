"""
UPLOAD APPROVED DATA
Upload only inspected and approved data to MongoDB Cloud

This ensures clean, validated data in your cloud database.

Usage:
    python upload_approved_data.py
"""

from cloud_mining_setup import CloudMiningSetup
from pathlib import Path
import json


def upload_approved_only():
    """Upload only approved data to cloud"""

    approved_dir = Path('data_mine/permanent_data/approved')

    if not approved_dir.exists():
        print("❌ No approved directory found!")
        print("   Run data inspection first:")
        print("   python data_inspector.py --batch")
        return

    # Get approved HDF5 files
    approved_files = list(approved_dir.glob('*.hdf5'))

    if not approved_files:
        print("⚠️  No approved files to upload!")
        print("   Run data inspection to approve files:")
        print("   python data_inspector.py --batch")
        return

    print("="*70)
    print("☁️  UPLOADING APPROVED DATA TO CLOUD")
    print("="*70)
    print(f"Approved files: {len(approved_files)}")
    print()

    # Connect to cloud
    cloud = CloudMiningSetup()

    if not cloud.client:
        print("❌ Cloud connection failed!")
        return

    uploaded = 0
    total_size = 0

    for hdf5_file in approved_files:
        # Find corresponding JSON
        json_file = approved_dir / f"{hdf5_file.stem}_reconciled.json"

        try:
            doc_id = cloud.upload_robot_sample(
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
    print(f"✅ Uploaded {uploaded}/{len(approved_files)} files")
    print(f"📦 Total size: {total_size/1024/1024:.2f} MB")
    print("="*70)

    # Show cloud status
    print()
    cloud.print_status()


if __name__ == '__main__':
    upload_approved_only()
