# 📱 MONITOR YOUR MINING FROM YOUR PHONE

Access your 24/7 mining operation from anywhere - perfect for checking during interview downtime!

## Quick Setup (10 minutes)

### Step 1: Get MongoDB Atlas (FREE Cloud Storage)

1. **Sign up** at https://cloud.mongodb.com
   - Use Google/GitHub login (fastest)
   - Select FREE tier (512MB)

2. **Create Cluster**
   - Click "Build a Database"
   - Choose "M0 FREE" tier
   - Select closest region (US East recommended)
   - Click "Create"

3. **Security Setup**
   ```
   Database Access:
   - Add user: swiftsyn
   - Password: [auto-generate and save]
   - Role: Atlas admin

   Network Access:
   - Click "Add IP Address"
   - Select "Allow access from anywhere" (0.0.0.0/0)
   - Confirm
   ```

4. **Get Connection String**
   - Click "Connect"
   - Choose "Connect your application"
   - Copy the string: `mongodb+srv://swiftsyn:<password>@cluster0.xxxxx.mongodb.net/`
   - Replace `<password>` with your password

### Step 2: Connect Your Mining to Cloud

On your computer, run:

```bash
# Set your MongoDB connection (replace with YOUR string)
export MONGODB_URI='mongodb+srv://swiftsyn:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/'

# Upload existing data to cloud
python cloud_mining_setup.py --upload

# Check status
python cloud_mining_setup.py --status
```

**Make it permanent** (add to `~/.zshrc` or `~/.bashrc`):
```bash
echo "export MONGODB_URI='mongodb+srv://swiftsyn:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/'" >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Modify Mining to Auto-Upload

We need to modify your mining to upload to cloud automatically. I'll do this for you!

## 📱 Access from Phone

### Option 1: MongoDB Mobile App (Easiest)

**Download:**
- iOS: https://apps.apple.com/app/mongodb-realm/id1462268006
- Android: https://play.android.com/store/apps/details?id=com.mongodb.realm

**Login:**
1. Open app
2. Login with same credentials
3. View your data in real-time!

### Option 2: Web Browser (Any Device)

1. Go to https://cloud.mongodb.com
2. Login
3. Click "Browse Collections"
4. See your data!

**Database: `data_mining_empire`**
- `robot_training_data` - Your mined samples
- `mining_statistics` - Stats and progress
- `video_metadata` - Source videos

## 📊 What You Can See

### Robot Training Data
```json
{
  "filename": "test_video_02_robotdata.hdf5",
  "size_bytes": 45231,
  "uploaded_at": "2025-12-03T14:30:00",
  "source": "youtube_mining",
  "metadata": {
    "action": "waving",
    "confidence": 0.92,
    "frames": 150
  }
}
```

### Mining Statistics
```json
{
  "timestamp": "2025-12-03T14:35:00",
  "videos_processed": 150,
  "videos_accepted": 45,
  "acceptance_rate": 0.30,
  "space_saved_mb": 140.5,
  "rate_limit_status": "OK - 23/70 this hour"
}
```

## 🎯 Quick Commands (from Phone Browser)

### MongoDB Shell (Web-based)

1. Go to your cluster → "Connect" → "MongoDB Shell"
2. Run these commands:

**Count total samples:**
```javascript
use data_mining_empire
db.robot_training_data.countDocuments()
```

**Get latest sample:**
```javascript
db.robot_training_data.findOne({}, {sort: {uploaded_at: -1}})
```

**Check mining stats:**
```javascript
db.mining_statistics.find().sort({timestamp: -1}).limit(1)
```

**Total data mined:**
```javascript
db.robot_training_data.aggregate([
  {$group: {_id: null, total_mb: {$sum: "$size_bytes"}}}
])
```

## 🔥 Real-Time Monitoring

### Status Dashboard (Python script that updates MongoDB)

I'll create a script that runs alongside your mining and updates stats every 5 minutes. You can see:
- Videos processed per hour
- Current acceptance rate
- Rate limit status
- Space saved
- Estimated completion time

All visible from your phone! 📱

## 🚨 Alerts (Future)

Set up MongoDB triggers to send you texts/emails when:
- Quality sample found (>80 score)
- Rate limit warning
- Error detected
- Daily goal reached

## ⚡ Quick Check Script

Save this as `phone_check.py` and run on computer (stats go to cloud):

```python
from cloud_mining_setup import CloudMiningSetup

cloud = CloudMiningSetup()
cloud.print_status()

# This updates MongoDB so you can see on phone
```

Then check from phone! 📱

---

**Next Steps:**
1. Sign up for MongoDB Atlas (5 min)
2. Get connection string
3. Run `export MONGODB_URI='your_string'`
4. Run `python cloud_mining_setup.py --upload`
5. Download MongoDB app on phone
6. Check your data anytime! 🎉
