# Quick Render Setup Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up (free account works)
3. Verify email

### Step 2: Deploy from GitHub
1. In Render dashboard: **New** → **Blueprint**
2. Connect GitHub (if not connected)
3. Select repository: `AI-News-Aggregator-Sanjay`
4. Select branch: `main`
5. Click **Apply** (Render reads `render.yaml` automatically)

### Step 3: Set Environment Variables
After services are created, go to `daily-digest-job` → **Environment** tab and fill in:

```
GEMINI_API_KEY=your_gemini_api_key      # Free from aistudio.google.com
MY_EMAIL=your.email@gmail.com
RECIPIENT_EMAIL=your.email@gmail.com
USER_NAME=YourName
APP_PASSWORD=your_16_char_app_password  # From myaccount.google.com/apppasswords
```

**Note**: `DATABASE_URL` is auto-set by Render - don't add it manually!

### Step 4: Test
1. Go to `daily-digest-job` → **Logs**
2. Click **Manual Deploy** to test immediately
3. Check your email inbox

## ✅ What Gets Created

- **PostgreSQL Database**: `ai-news-aggregator-db` (free tier)
- **Cron Job**: Runs `python main.py` daily at 7:00 AM IST (`30 1 * * *` UTC)

## 📝 Schedule Customization

Edit `render.yaml` to change schedule:
```yaml
schedule: "30 1 * * *"  # 7:00 AM IST (1:30 AM UTC)
# or schedule: "0 7 * * *"  # 7:00 AM UTC
```

Then push to GitHub - Render auto-updates.

## 🔍 Troubleshooting

**Database connection fails?**
- Check `DATABASE_URL` is set (should be automatic)
- Verify database service is running

**Email not sending?**
- Verify Gmail app password (not regular password)
- Check `MY_EMAIL` and `APP_PASSWORD` are correct

**Cron not running?**
- Check logs in Render dashboard
- Verify schedule syntax

## 📚 Full Documentation

See `DEPLOYMENT.md` for detailed instructions.

