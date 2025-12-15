"""
MONGODB DATA STORAGE

Structures all mined robot training data in MongoDB for easy querying and management.

Collections:
- videos: Metadata about each video (URL, quality score, etc.)
- robot_data: Extracted robot training data (positions, actions, etc.)
- mining_sessions: Statistics about mining operations
- actions: Organized by action category

Benefits:
- Query by action type: "Give me all 'opening' actions"
- Filter by quality: "Only videos with score > 80"
- Track lineage: "Which YouTube video generated this training sample?"
- Analytics: "What's my acceptance rate for 'pouring' videos?"
"""

from pymongo import MongoClient
from datetime import datetime
import json
from pathlib import Path


class RobotDataStorage:
    """
    MongoDB storage for robot training data mining operation
    """

    def __init__(self, mongo_uri='mongodb://localhost:27017/', db_name='robot_training_data'):
        """
        Initialize MongoDB connection

        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
        """
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]

            # Collections
            self.videos = self.db['videos']
            self.robot_data = self.db['robot_data']
            self.mining_sessions = self.db['mining_sessions']
            self.actions = self.db['actions']

            # Create indexes for fast querying
            self._create_indexes()

            print(f"✅ Connected to MongoDB: {db_name}")

        except Exception as e:
            print(f"⚠️  MongoDB connection failed: {e}")
            print("   Running in JSON-only mode (no MongoDB)")
            self.client = None

    def _create_indexes(self):
        """Create indexes for fast queries"""
        if not self.client:
            return

        # Video indexes
        self.videos.create_index('video_id')
        self.videos.create_index('quality_score')
        self.videos.create_index('action_category')
        self.videos.create_index('accepted')

        # Robot data indexes
        self.robot_data.create_index('video_id')
        self.robot_data.create_index('action')
        self.robot_data.create_index('confidence')

        # Action indexes
        self.actions.create_index('action_type')
        self.actions.create_index('quality_score')

    def store_video_analysis(self, video_path, quality_result, search_query, accepted):
        """
        Store video quality analysis results

        Args:
            video_path: Path to video file
            quality_result: Quality scorer result dict
            search_query: YouTube search query used
            accepted: Whether video was accepted (quality >= threshold)

        Returns:
            video_id: MongoDB document ID
        """
        if not self.client:
            return None

        video_path = Path(video_path)

        document = {
            'video_id': video_path.stem,
            'filename': video_path.name,
            'filepath': str(video_path),
            'search_query': search_query,
            'quality_score': quality_result['score'],
            'quality_rating': quality_result['rating'],
            'accepted': accepted,
            'metadata': quality_result.get('metadata', {}),
            'breakdown': quality_result.get('breakdown', {}),
            'recommendation': quality_result.get('recommendation', ''),
            'analyzed_at': datetime.now(),
            'action_category': self._infer_action_category(search_query)
        }

        result = self.videos.insert_one(document)
        return result.inserted_id

    def store_robot_data(self, video_path, robot_data):
        """
        Store extracted robot training data

        Args:
            video_path: Path to video file
            robot_data: Robot data dict (from reconciled.json or robot_data.json)

        Returns:
            data_id: MongoDB document ID
        """
        if not self.client:
            return None

        video_path = Path(video_path)

        document = {
            'video_id': video_path.stem,
            'action': robot_data.get('action'),
            'confidence': robot_data.get('confidence'),
            'method': robot_data.get('method'),
            'reasoning': robot_data.get('reasoning'),
            'conflict_detected': robot_data.get('conflict_detected', False),
            'kinematics_summary': self._summarize_kinematics(robot_data.get('kinematics', {})),
            'extracted_at': datetime.now(),
            'full_data_path': str(robot_data.get('output_files', {}).get('robot_data', ''))
        }

        result = self.robot_data.insert_one(document)

        # Also store in actions collection for easier querying
        self._store_action(video_path, robot_data, document)

        return result.inserted_id

    def _store_action(self, video_path, robot_data, data_doc):
        """Store in actions collection organized by action type"""
        if not self.client:
            return

        # Get video quality score
        video_info = self.videos.find_one({'video_id': Path(video_path).stem})
        quality_score = video_info.get('quality_score', 0) if video_info else 0

        action_doc = {
            'action_type': robot_data.get('action'),
            'video_id': Path(video_path).stem,
            'confidence': robot_data.get('confidence'),
            'quality_score': quality_score,
            'method': robot_data.get('method'),
            'kinematics_summary': data_doc['kinematics_summary'],
            'created_at': datetime.now()
        }

        self.actions.insert_one(action_doc)

    def _summarize_kinematics(self, kinematics):
        """Create compact summary of kinematics data"""
        if not kinematics:
            return {}

        positions = kinematics.get('positions', [])
        velocities = kinematics.get('velocities', [])

        if not positions:
            return {}

        # Calculate summary statistics
        import numpy as np
        positions_array = np.array(positions)

        return {
            'num_frames': len(positions),
            'duration': kinematics.get('timestamps', [0])[-1] if kinematics.get('timestamps') else 0,
            'start_position': positions[0],
            'end_position': positions[-1],
            'net_displacement': [positions[-1][i] - positions[0][i] for i in range(3)],
            'max_velocity': float(np.max(np.abs(velocities))) if velocities else 0,
            'total_distance': float(np.sum(np.linalg.norm(np.diff(positions_array, axis=0), axis=1)))
        }

    def _infer_action_category(self, search_query):
        """Infer action category from search query"""
        query_lower = search_query.lower()

        if 'open' in query_lower:
            return 'opening'
        elif 'close' in query_lower or 'closing' in query_lower:
            return 'closing'
        elif 'pour' in query_lower:
            return 'pouring'
        elif 'pick' in query_lower or 'grasp' in query_lower:
            return 'grasping'
        elif 'place' in query_lower or 'put' in query_lower:
            return 'placing'
        elif 'push' in query_lower:
            return 'pushing'
        elif 'pull' in query_lower:
            return 'pulling'
        elif 'twist' in query_lower or 'turn' in query_lower:
            return 'twisting'
        elif 'slide' in query_lower:
            return 'sliding'
        elif 'lift' in query_lower:
            return 'lifting'
        else:
            return 'other'

    def start_mining_session(self, config):
        """Record start of mining session"""
        if not self.client:
            return None

        session = {
            'started_at': datetime.now(),
            'config': config,
            'status': 'running',
            'videos_mined': 0,
            'videos_accepted': 0
        }

        result = self.mining_sessions.insert_one(session)
        return result.inserted_id

    def update_mining_session(self, session_id, stats):
        """Update mining session statistics"""
        if not self.client or not session_id:
            return

        self.mining_sessions.update_one(
            {'_id': session_id},
            {'$set': stats}
        )

    def end_mining_session(self, session_id):
        """Mark mining session as complete"""
        if not self.client or not session_id:
            return

        self.mining_sessions.update_one(
            {'_id': session_id},
            {'$set': {
                'ended_at': datetime.now(),
                'status': 'completed'
            }}
        )

    # Query methods for data retrieval

    def get_videos_by_action(self, action_category, min_quality=70):
        """Get all videos for a specific action category above quality threshold"""
        if not self.client:
            return []

        return list(self.videos.find({
            'action_category': action_category,
            'accepted': True,
            'quality_score': {'$gte': min_quality}
        }).sort('quality_score', -1))

    def get_actions_by_type(self, action_type, min_confidence=0.7):
        """Get all training samples for a specific action type"""
        if not self.client:
            return []

        return list(self.actions.find({
            'action_type': action_type,
            'confidence': {'$gte': min_confidence}
        }).sort('quality_score', -1))

    def get_statistics(self):
        """Get overall mining statistics"""
        if not self.client:
            return {}

        total_videos = self.videos.count_documents({})
        accepted_videos = self.videos.count_documents({'accepted': True})

        # Action distribution
        pipeline = [
            {'$group': {
                '_id': '$action_category',
                'count': {'$sum': 1},
                'avg_quality': {'$avg': '$quality_score'}
            }},
            {'$sort': {'count': -1}}
        ]
        action_dist = list(self.videos.aggregate(pipeline))

        # Quality distribution
        quality_ranges = [
            ('Excellent (80-100)', 80, 100),
            ('Good (70-80)', 70, 80),
            ('Fair (50-70)', 50, 70),
            ('Poor (0-50)', 0, 50)
        ]
        quality_dist = {}
        for label, min_q, max_q in quality_ranges:
            count = self.videos.count_documents({
                'quality_score': {'$gte': min_q, '$lt': max_q}
            })
            quality_dist[label] = count

        return {
            'total_videos': total_videos,
            'accepted_videos': accepted_videos,
            'rejected_videos': total_videos - accepted_videos,
            'acceptance_rate': accepted_videos / total_videos if total_videos > 0 else 0,
            'action_distribution': action_dist,
            'quality_distribution': quality_dist,
            'total_training_samples': self.actions.count_documents({})
        }

    def print_statistics(self):
        """Print formatted statistics"""
        stats = self.get_statistics()

        print()
        print("="*70)
        print("📊 MONGODB STORAGE STATISTICS")
        print("="*70)
        print(f"Total videos analyzed: {stats['total_videos']}")
        print(f"Accepted: {stats['accepted_videos']} ({stats['acceptance_rate']:.1%})")
        print(f"Rejected: {stats['rejected_videos']}")
        print(f"Total training samples: {stats['total_training_samples']}")
        print()

        print("📊 ACTION DISTRIBUTION:")
        for item in stats['action_distribution']:
            category = item['_id'] or 'unknown'
            count = item['count']
            avg_q = item['avg_quality']
            print(f"   {category:15s}: {count:4d} videos (avg quality: {avg_q:.1f})")

        print()
        print("📊 QUALITY DISTRIBUTION:")
        for label, count in stats['quality_distribution'].items():
            print(f"   {label:20s}: {count:4d} videos")

        print("="*70)
        print()

    def export_dataset_manifest(self, output_file='dataset_manifest.json'):
        """
        Export complete dataset manifest for distribution

        This creates a JSON file listing all training data suitable for:
        - Sharing with customers
        - Dataset documentation
        - Reproducibility
        """
        if not self.client:
            print("⚠️  MongoDB not connected, cannot export manifest")
            return

        manifest = {
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'videos': list(self.videos.find({'accepted': True}, {
                '_id': 0,
                'video_id': 1,
                'quality_score': 1,
                'action_category': 1,
                'metadata': 1
            })),
            'actions': list(self.actions.find({}, {
                '_id': 0,
                'action_type': 1,
                'video_id': 1,
                'confidence': 1,
                'quality_score': 1
            }))
        }

        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"✅ Dataset manifest exported to: {output_file}")
        print(f"   {len(manifest['videos'])} videos")
        print(f"   {len(manifest['actions'])} training samples")


def main():
    """
    Test MongoDB storage
    """
    storage = RobotDataStorage()
    storage.print_statistics()


if __name__ == '__main__':
    main()
