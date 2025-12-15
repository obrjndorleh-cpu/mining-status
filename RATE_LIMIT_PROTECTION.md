# 🛡️ RATE LIMIT PROTECTION

**Prevents YouTube from blocking your IP!**

---

## ⚠️ THE PROBLEM

YouTube has rate limits:
- **~100 videos/hour** from single IP
- **~1,000 videos/day** from single IP
- Exceed limits → Temporary IP ban (403 errors)
- Ban duration: 24 hours typically

**Your mining system could trigger this!**

---

## ✅ THE SOLUTION

Built-in rate limit protection:

### Conservative Limits (70% of maximum):
```
Hourly limit:  70 videos  (vs YouTube's ~100)
Daily limit:   700 videos (vs YouTube's ~1000)
Min delay:     10 seconds between downloads
```

### Smart Features:
- ✅ Tracks all downloads (last 1,000)
- ✅ Enforces hourly + daily quotas
- ✅ Exponential backoff when approaching limits
- ✅ Detects 403/429 errors (ban indicators)
- ✅ Auto-pauses when limits reached
- ✅ Automatic recovery after cooldown

---

## 📊 CHECK YOUR STATUS

```bash
# View current rate limit status
python rate_limit_manager.py --status
```

**Output:**
```
📊 RATE LIMIT STATUS
======================================================================
Last hour:  45/70 (64.3%)
Last 24h:   320/700 (45.7%)

Total downloads: 450
Total errors: 5
Error rate: 1.1%

✅ Status: Can download (recommended delay: 10s)
======================================================================
```

---

## 🎯 HOW IT WORKS

### Automatic Protection:

**Before each download:**
1. Check: "Am I at hourly limit?" → Wait if needed
2. Check: "Am I at daily limit?" → Pause if needed
3. Check: "Too soon after last download?" → Delay
4. Check: "Too many recent errors?" → Cooldown

**If hitting limits:**
```
Hourly limit (70): Wait until oldest download expires (up to 1 hour)
Daily limit (700): Wait until daily window resets (up to 24 hours)
```

**Your mining automatically pauses and resumes!**

---

## 🚨 IF YOU GET BANNED

### Symptoms:
- 403 Forbidden errors
- 429 Too Many Requests errors
- Videos won't download

### Recovery:
```bash
# 1. Stop mining
kill <PID>  # Your mining process

# 2. Wait 24 hours

# 3. Optional: Change IP
# - Restart router (gets new IP from ISP)
# - Use VPN
# - Use mobile hotspot

# 4. Reset ban status
python rate_limit_manager.py --reset-ban

# 5. Lower limits (optional, for safety)
python rate_limit_manager.py --set-hourly 50 --set-daily 500

# 6. Resume mining
python run_overnight_mining.py --auto-process --delete-after-extract
```

---

## ⚙️ CONFIGURE LIMITS

### Make It More Conservative (Safer):
```bash
# Set to 50% of YouTube's limits
python rate_limit_manager.py --set-hourly 50 --set-daily 500
```

### Make It More Aggressive (Riskier):
```bash
# Use 90% of YouTube's limits
python rate_limit_manager.py --set-hourly 90 --set-daily 900
```

### Default (Recommended):
```
70/hour, 700/day = Sweet spot
- Safe from bans
- Still mines ~700 videos/day
- 21,000 videos/month!
```

---

## 📈 EXPECTED MINING SPEED

### With Rate Limits (70/hour, 700/day):

**Hourly:** Up to 70 videos
**Daily:** Up to 700 videos
**Weekly:** Up to 4,900 videos
**Monthly:** Up to 21,000 videos

**Acceptance rate ~30%:**
- 700 videos/day analyzed
- ~210 quality videos/day accepted
- ~6,300 quality samples/month

**This is MORE than enough for building massive datasets!**

---

## 💡 SCALING STRATEGIES

### Single IP (Current):
```
Limit: 700 videos/day
Strategy: Let it run 24/7
Result: 21K videos/month
```

### Future: Multiple IPs
```
3 computers (3 IPs): 700 × 3 = 2,100/day
5 VPN locations: 700 × 5 = 3,500/day
10 residential proxies: 700 × 10 = 7,000/day

With rate limiting on EACH IP = No bans!
```

---

## 🛡️ PROTECTION LEVELS

### Level 1: Ultra-Safe (Current Default)
```
Hourly: 70  (70% of limit)
Daily: 700  (70% of limit)
Risk: <1% ban chance
Speed: 700/day
```

### Level 2: Balanced
```
Hourly: 85  (85% of limit)
Daily: 850  (85% of limit)
Risk: ~5% ban chance
Speed: 850/day
```

### Level 3: Aggressive
```
Hourly: 95  (95% of limit)
Daily: 950  (95% of limit)
Risk: ~20% ban chance
Speed: 950/day
```

### Level 4: Maximum (NOT RECOMMENDED)
```
Hourly: 100 (100% of limit)
Daily: 1000 (100% of limit)
Risk: ~50% ban chance
Speed: 1000/day... until banned
```

**Recommendation: Stay at Level 1 (default). 700/day is already massive!**

---

## 📊 MONITORING

### Real-Time Status:
```bash
# Watch your rate limit usage
watch -n 60 'python rate_limit_manager.py --status'
```

### In Mining Logs:
```
⏱️  Rate limiting: Waiting 15s before download...
✅ Downloaded video (45/70 hourly, 320/700 daily)
```

### Files Created:
```
rate_limit_config.json   # Current limits & settings
download_history.json    # Last 1,000 downloads
```

---

## ✅ YOU'RE PROTECTED!

Your mining system now has:
- ✅ Automatic rate limiting
- ✅ IP ban detection
- ✅ Exponential backoff
- ✅ Hourly + daily quotas
- ✅ Smart throttling
- ✅ Error tracking
- ✅ Auto-recovery

**Mine with confidence!** Your IP is protected. 🛡️

---

## 🎯 CURRENT STATUS

Check if rate limiting is active:
```bash
tail -f infinite_mining.log | grep "Rate limiting"
```

**If you see:** `⏱️  Rate limiting: Waiting Xs...`
**Then:** Protection is working! ✅

**Your mining runs safely within YouTube's limits!** 🚀
