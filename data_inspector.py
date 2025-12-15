"""
DATA INSPECTOR
Inspect and validate HDF5 robot training data before cloud upload

Features:
- View HDF5 contents
- Validate data quality
- Check for errors/corruption
- Approve/reject for cloud upload
- Batch inspection

Usage:
    python data_inspector.py --data-dir data_mine/permanent_data/hdf5
"""

import h5py
import json
import numpy as np
from pathlib import Path
from datetime import datetime


class DataInspector:
    """Inspect robot training data before cloud upload"""

    def __init__(self, data_dir='data_mine/permanent_data/hdf5'):
        self.data_dir = Path(data_dir)
        self.json_dir = self.data_dir.parent / 'json'

        self.approved_dir = self.data_dir.parent / 'approved'
        self.rejected_dir = self.data_dir.parent / 'rejected'

        self.approved_dir.mkdir(exist_ok=True)
        self.rejected_dir.mkdir(exist_ok=True)

        self.inspection_log = self.data_dir.parent / 'inspection_log.json'
        self.load_log()

    def load_log(self):
        """Load inspection history"""
        if self.inspection_log.exists():
            with open(self.inspection_log, 'r') as f:
                self.log = json.load(f)
        else:
            self.log = {
                'inspected': [],
                'approved': [],
                'rejected': [],
                'stats': {
                    'total_inspected': 0,
                    'total_approved': 0,
                    'total_rejected': 0
                }
            }

    def save_log(self):
        """Save inspection history"""
        with open(self.inspection_log, 'w') as f:
            json.dump(self.log, f, indent=2)

    def validate_hdf5(self, hdf5_path):
        """
        Validate HDF5 file quality

        Returns:
            dict with validation results
        """
        hdf5_path = Path(hdf5_path)

        validation = {
            'filename': hdf5_path.name,
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        try:
            with h5py.File(hdf5_path, 'r') as f:
                # Check required datasets
                required = ['pose/keypoints']
                for key in required:
                    if key not in f:
                        validation['valid'] = False
                        validation['errors'].append(f"Missing required dataset: {key}")

                # Validate pose data
                if 'pose/keypoints' in f:
                    pose_data = f['pose/keypoints'][:]

                    # Check shape
                    if pose_data.shape[0] < 33:
                        validation['errors'].append(f"Incomplete pose data: {pose_data.shape[0]}/33 keypoints")
                        validation['valid'] = False

                    # Check for NaN/Inf
                    if np.any(np.isnan(pose_data)):
                        validation['warnings'].append("Contains NaN values")

                    if np.any(np.isinf(pose_data)):
                        validation['warnings'].append("Contains Inf values")

                    # Check visibility scores
                    if pose_data.shape[1] >= 4:  # Has visibility
                        visibility = pose_data[:, 3]
                        avg_visibility = np.mean(visibility)

                        if avg_visibility < 0.3:
                            validation['warnings'].append(f"Low average visibility: {avg_visibility:.2f}")

                        validation['stats']['avg_visibility'] = float(avg_visibility)
                        validation['stats']['visible_keypoints'] = int(np.sum(visibility > 0.5))

                    validation['stats']['pose_keypoints'] = pose_data.shape[0]

                # Validate hand data
                left_hand = 'hands/left' in f
                right_hand = 'hands/right' in f

                validation['stats']['left_hand'] = left_hand
                validation['stats']['right_hand'] = right_hand

                if left_hand:
                    left_data = f['hands/left'][:]
                    validation['stats']['left_hand_keypoints'] = left_data.shape[0]

                if right_hand:
                    right_data = f['hands/right'][:]
                    validation['stats']['right_hand_keypoints'] = right_data.shape[0]

        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"File read error: {str(e)}")

        return validation

    def inspect_file(self, hdf5_path):
        """
        Inspect a single HDF5 file

        Returns:
            dict with inspection results and recommendation
        """
        hdf5_path = Path(hdf5_path)

        print(f"\n{'='*70}")
        print(f"INSPECTING: {hdf5_path.name}")
        print(f"{'='*70}")

        # Validate file
        validation = self.validate_hdf5(hdf5_path)

        # Show validation results
        print(f"\nValidation: {'✅ PASSED' if validation['valid'] else '❌ FAILED'}")

        if validation['errors']:
            print("\nErrors:")
            for error in validation['errors']:
                print(f"  ❌ {error}")

        if validation['warnings']:
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  ⚠️  {warning}")

        print("\nStats:")
        for key, value in validation['stats'].items():
            print(f"  • {key}: {value}")

        # Check JSON metadata
        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            with open(json_path, 'r') as f:
                metadata = json.load(f)
                print(f"\nMetadata:")
                print(f"  • Action: {metadata.get('action', 'N/A')}")
                print(f"  • Confidence: {metadata.get('confidence', 'N/A')}")
                print(f"  • Method: {metadata.get('method', 'N/A')}")

        # Recommendation
        if validation['valid'] and len(validation['warnings']) == 0:
            recommendation = "APPROVE"
            print(f"\n✅ RECOMMENDATION: APPROVE for cloud upload")
        elif validation['valid'] and len(validation['warnings']) <= 2:
            recommendation = "APPROVE_WITH_WARNINGS"
            print(f"\n⚠️  RECOMMENDATION: APPROVE (with warnings)")
        else:
            recommendation = "REJECT"
            print(f"\n❌ RECOMMENDATION: REJECT (quality issues)")

        return {
            'file': str(hdf5_path),
            'validation': validation,
            'recommendation': recommendation,
            'inspected_at': datetime.now().isoformat()
        }

    def batch_inspect(self, auto_approve=False, auto_reject=False):
        """
        Inspect all uninspected files in data directory

        Args:
            auto_approve: Automatically approve files with APPROVE recommendation
            auto_reject: Automatically reject files with REJECT recommendation
        """
        hdf5_files = list(self.data_dir.glob('*.hdf5'))

        # Filter out already inspected
        inspected_files = set(self.log['inspected'])
        uninspected = [f for f in hdf5_files if f.name not in inspected_files]

        if not uninspected:
            print("✅ All files already inspected!")
            return

        print("="*70)
        print(f"BATCH INSPECTION: {len(uninspected)} files")
        print("="*70)

        for idx, hdf5_file in enumerate(uninspected):
            print(f"\n[{idx+1}/{len(uninspected)}]")

            result = self.inspect_file(hdf5_file)

            # Auto-decision or manual?
            if auto_approve and result['recommendation'] in ['APPROVE', 'APPROVE_WITH_WARNINGS']:
                decision = 'approve'
                print("\n🤖 AUTO-APPROVED")
            elif auto_reject and result['recommendation'] == 'REJECT':
                decision = 'reject'
                print("\n🤖 AUTO-REJECTED")
            else:
                # Manual decision
                print("\n" + "-"*70)
                decision = input("Decision [a]pprove / [r]eject / [s]kip: ").lower()

            # Process decision
            if decision in ['a', 'approve']:
                self.approve_file(hdf5_file)
                print(f"✅ Approved: {hdf5_file.name}")
            elif decision in ['r', 'reject']:
                self.reject_file(hdf5_file)
                print(f"❌ Rejected: {hdf5_file.name}")
            else:
                print(f"⏭️  Skipped: {hdf5_file.name}")

            # Log inspection
            self.log['inspected'].append(hdf5_file.name)
            self.save_log()

        print("\n" + "="*70)
        print("INSPECTION COMPLETE")
        print("="*70)
        self.print_summary()

    def approve_file(self, hdf5_path):
        """Move file to approved directory"""
        hdf5_path = Path(hdf5_path)
        dest = self.approved_dir / hdf5_path.name
        hdf5_path.rename(dest)

        # Move JSON too
        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            json_dest = self.approved_dir / json_path.name
            json_path.rename(json_dest)

        self.log['approved'].append(hdf5_path.name)
        self.log['stats']['total_approved'] += 1

    def reject_file(self, hdf5_path):
        """Move file to rejected directory"""
        hdf5_path = Path(hdf5_path)
        dest = self.rejected_dir / hdf5_path.name
        hdf5_path.rename(dest)

        # Move JSON too
        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            json_dest = self.rejected_dir / json_path.name
            json_path.rename(json_dest)

        self.log['rejected'].append(hdf5_path.name)
        self.log['stats']['total_rejected'] += 1

    def print_summary(self):
        """Print inspection summary"""
        print(f"\nInspection Summary:")
        print(f"  Total inspected: {len(self.log['inspected'])}")
        print(f"  Approved: {self.log['stats']['total_approved']}")
        print(f"  Rejected: {self.log['stats']['total_rejected']}")
        print(f"\nApproved files ready for cloud upload at:")
        print(f"  {self.approved_dir}")


def main():
    """Run data inspector"""
    import argparse

    parser = argparse.ArgumentParser(description='Inspect robot training data')
    parser.add_argument('--data-dir', default='data_mine/permanent_data/hdf5',
                       help='Data directory to inspect')
    parser.add_argument('--file', help='Inspect single file')
    parser.add_argument('--batch', action='store_true',
                       help='Batch inspect all files')
    parser.add_argument('--auto-approve', action='store_true',
                       help='Auto-approve files with APPROVE recommendation')
    parser.add_argument('--auto-reject', action='store_true',
                       help='Auto-reject files with REJECT recommendation')

    args = parser.parse_args()

    inspector = DataInspector(data_dir=args.data_dir)

    if args.file:
        # Inspect single file
        result = inspector.inspect_file(args.file)
    elif args.batch:
        # Batch inspect
        inspector.batch_inspect(
            auto_approve=args.auto_approve,
            auto_reject=args.auto_reject
        )
    else:
        print("Usage:")
        print("  Inspect single file: python data_inspector.py --file path/to/file.hdf5")
        print("  Batch inspect: python data_inspector.py --batch")
        print("  Auto-approve: python data_inspector.py --batch --auto-approve")


if __name__ == '__main__':
    main()
