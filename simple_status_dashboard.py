"""
SIMPLE STATUS DASHBOARD
Access your mining stats from anywhere via public URL!

Uses Streamlit + ngrok/cloudflare tunnel for public access
"""

import streamlit as st
from cloud_mining_setup import CloudMiningSetup
from datetime import datetime, timedelta
from pathlib import Path
import json
import os

# Set page config
st.set_page_config(
    page_title="Mining Status",
    page_icon="⛏️",
    layout="wide"
)

# MongoDB connection
@st.cache_resource
def get_cloud_connection():
    return CloudMiningSetup()

def load_rate_limit_status():
    """Load current rate limit status"""
    rate_limit_file = Path('rate_limit_config.json')
    if not rate_limit_file.exists():
        return None

    with open(rate_limit_file, 'r') as f:
        config = json.load(f)
        history = config.get('download_history', [])

        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        downloads_hour = sum(
            1 for d in history
            if datetime.fromisoformat(d['timestamp']) > one_hour_ago
        )
        downloads_day = sum(
            1 for d in history
            if datetime.fromisoformat(d['timestamp']) > one_day_ago
        )

        return {
            'downloads_hour': downloads_hour,
            'downloads_day': downloads_day,
            'hourly_limit': config.get('max_per_hour', 70),
            'daily_limit': config.get('max_per_day', 700),
            'hourly_percent': (downloads_hour / 70) * 100,
            'daily_percent': (downloads_day / 700) * 100,
        }

def load_local_stats():
    """Load stats from permanent_data folder"""
    stats = {}

    # Count HDF5 files
    perm_data = Path('permanent_data')
    if perm_data.exists():
        hdf5_files = list(perm_data.glob('hdf5/*.hdf5'))
        stats['local_samples'] = len(hdf5_files)
        total_size = sum(f.stat().st_size for f in hdf5_files)
        stats['local_data_mb'] = total_size / (1024 * 1024)

    # Extract and delete log
    extract_log = Path('extract_and_delete.log')
    if extract_log.exists():
        with open(extract_log, 'r') as f:
            log_data = json.load(f)
            stats['videos_deleted'] = log_data.get('videos_deleted', 0)
            stats['space_saved_mb'] = log_data.get('space_saved_mb', 0)

    return stats

def main():
    # Header
    st.title("⛏️ Mining Status Dashboard")
    st.caption("Real-time monitoring - Updates every 30 seconds")

    # Auto-refresh every 30 seconds
    st.markdown("""
    <script>
    setTimeout(function(){
        window.location.reload();
    }, 30000);
    </script>
    """, unsafe_allow_html=True)

    # Get data
    cloud = get_cloud_connection()
    rate_limit = load_rate_limit_status()
    local_stats = load_local_stats()

    # Cloud connection status
    if cloud.client and cloud.is_cloud:
        st.success("☁️ Connected to Cloud")
    else:
        st.error("❌ Cloud Disconnected")

    st.markdown("---")

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if cloud.client:
            cloud_stats = cloud.get_mining_statistics()
            st.metric(
                "☁️ Cloud Samples",
                f"{cloud_stats.get('robot_samples', 0)}",
                help="Total samples in cloud storage"
            )
        else:
            st.metric("☁️ Cloud Samples", "N/A")

    with col2:
        local_samples = local_stats.get('local_samples', 0)
        st.metric(
            "💾 Local Samples",
            f"{local_samples}",
            help="Samples on this computer (pending upload)"
        )

    with col3:
        space_saved = local_stats.get('space_saved_mb', 0)
        st.metric(
            "🗑️ Space Saved",
            f"{space_saved:.1f} MB",
            help="Disk space freed by auto-delete"
        )

    with col4:
        videos_deleted = local_stats.get('videos_deleted', 0)
        st.metric(
            "🎬 Videos Deleted",
            f"{videos_deleted}",
            help="Videos deleted after extraction"
        )

    st.markdown("---")

    # Rate limits
    st.subheader("🚦 Rate Limit Status")

    if rate_limit:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Hourly (70 max)")
            hourly_percent = rate_limit['hourly_percent']
            st.progress(hourly_percent / 100)
            st.markdown(f"**{rate_limit['downloads_hour']}/70** downloads this hour")

            if hourly_percent < 70:
                st.success(f"✅ OK - {70 - rate_limit['downloads_hour']} remaining")
            elif hourly_percent < 90:
                st.warning(f"⚠️ Approaching limit - {70 - rate_limit['downloads_hour']} remaining")
            else:
                st.error("🛑 Near limit - Slowing down")

        with col2:
            st.markdown("### Daily (700 max)")
            daily_percent = rate_limit['daily_percent']
            st.progress(daily_percent / 100)
            st.markdown(f"**{rate_limit['downloads_day']}/700** downloads today")

            if daily_percent < 70:
                st.success(f"✅ OK - {700 - rate_limit['downloads_day']} remaining")
            elif daily_percent < 90:
                st.warning(f"⚠️ Approaching limit - {700 - rate_limit['downloads_day']} remaining")
            else:
                st.error("🛑 Near limit - Slowing down")
    else:
        st.info("Rate limit data not available")

    st.markdown("---")

    # Mining statistics from cloud
    st.subheader("📊 Mining Statistics")

    if cloud.client:
        try:
            # Get latest stats from MongoDB
            latest_stats = list(cloud.db['mining_statistics'].find().sort('timestamp', -1).limit(1))

            if latest_stats:
                stats = latest_stats[0]

                col1, col2, col3 = st.columns(3)

                with col1:
                    if 'mining_speed' in stats:
                        speed = stats['mining_speed']
                        st.metric(
                            "⚡ Mining Speed",
                            f"{speed.get('samples_per_hour', 0):.1f}/hour"
                        )
                        st.caption(f"Est. daily: {speed.get('estimated_daily', 0):.0f}")

                with col2:
                    uptime = stats.get('uptime_hours', 0)
                    st.metric("⏱️ Uptime", f"{uptime:.1f} hours")

                with col3:
                    last_update = stats.get('timestamp')
                    if last_update:
                        st.metric("🕐 Last Update", last_update.strftime("%H:%M:%S"))
            else:
                st.info("No statistics available yet. Stats update every 5 minutes.")

        except Exception as e:
            st.error(f"Error loading stats: {e}")

    st.markdown("---")

    # Recent samples
    st.subheader("📦 Recent Samples")

    if cloud.client:
        try:
            recent = list(cloud.robot_data.find().sort('uploaded_at', -1).limit(5))

            if recent:
                for sample in recent:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.text(sample.get('filename', 'Unknown'))
                    with col2:
                        size_kb = sample.get('size_bytes', 0) / 1024
                        st.text(f"{size_kb:.1f} KB")
                    with col3:
                        uploaded = sample.get('uploaded_at')
                        if uploaded:
                            st.text(uploaded.strftime("%H:%M"))
            else:
                st.info("No samples in cloud yet")

        except Exception as e:
            st.error(f"Error loading samples: {e}")

    # Footer
    st.markdown("---")
    st.caption(f"🔄 Auto-refreshes every 30 seconds | Last refresh: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == '__main__':
    main()
