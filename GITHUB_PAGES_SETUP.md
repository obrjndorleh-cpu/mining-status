# GitHub Pages Setup for Phone Monitoring

Monitor your mining operation from anywhere via your phone!

## Quick Setup (5 minutes)

### 1. Initialize Git Repository

```bash
cd /Users/swiftsyn/video_intelligence_system

# Initialize git
git init

# Add files
git add .

# Create initial commit
git commit -m "Initial commit - Video Intelligence System"
```

### 2. Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., `video-intelligence-mining`)
3. **DO NOT** initialize with README, .gitignore, or license
4. Copy the repository URL

### 3. Connect to GitHub

```bash
# Add remote (replace YOUR_USERNAME and YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 4. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Source", select **main** branch
4. Select **/docs** folder
5. Click **Save**
6. Wait 1-2 minutes for deployment

### 5. Start Auto-Updates

```bash
# Run in background to auto-update GitHub Pages every 2 minutes
nohup python auto_push_status.py > github_push.log 2>&1 &
echo "GitHub auto-push PID: $!"
```

## Access Dashboard

**From any device:**
- URL: `https://YOUR_USERNAME.github.io/YOUR_REPO/`
- Auto-refreshes every 60 seconds
- Mobile-friendly design

## Alternative: Quick Test Without GitHub

View dashboard locally on your Mac:

```bash
# Generate dashboard
python web_dashboard_generator.py

# Open in browser
open docs/index.html
```

## Commands

### Generate Dashboard Once
```bash
python web_dashboard_generator.py
```

### Auto-Update GitHub Pages
```bash
python auto_push_status.py
```

### Stop Auto-Updates
```bash
# Find PID
ps aux | grep auto_push_status

# Kill process
kill <PID>
```

## What Gets Updated

The dashboard shows:
- ✅ Mining process status (Running/Stopped)
- 📊 Gate 1 progress (11/100)
- ⛏️ Mining statistics (accepted/rejected/skipped)
- 🔒 Deduplication status
- 📁 Recent files with timestamps
- 🔄 Auto-refresh every 60 seconds

## Troubleshooting

### GitHub Pages not working?
- Check Settings → Pages is enabled
- Verify `/docs` folder is selected
- Wait 2-3 minutes after first setup

### Auto-push failing?
- Make sure git credentials are configured
- Check `github_push.log` for errors
- Verify remote repository exists

### Dashboard not updating?
- Check if auto_push_status.py is running: `ps aux | grep auto_push`
- Verify dashboard generates: `python web_dashboard_generator.py`
- Check git status: `git status`

## Security Note

This creates a **public** GitHub repository. The dashboard does NOT contain:
- API keys
- Private data
- File contents

Only shows:
- File counts
- Timestamps
- Mining statistics
- Process status
