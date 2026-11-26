# Render Deployment Guide: News2U

Deploy **News2U** (AI News Aggregator) on **Render** with 100% Free Tier support using our updated Blueprint (`render.yaml`).

---

## 💡 Why the Cron Error Happened
Render's official policy:
- **Web Services**: Available on `plan: free` (100% Free).
- **PostgreSQL Databases**: Available on `plan: free` (100% Free).
- **Cron Jobs**: **Do NOT have a free plan** (Render requires `plan: starter`, which is a paid plan).

### 🎯 The 100% Free Solution ($0/month):
We optimized the architecture so you don't have to pay for a cron job:
1. **Web Service (`news2u`)**: Serves the landing page and provides a webhook endpoint at `https://news2u.onrender.com/api/cron/run`.
2. **PostgreSQL Database (`news2u-db`)**: Stores all articles and subscribers for free.
3. **Daily Trigger (100% Free)**:
   - **GitHub Actions**: Automatically triggers the daily pipeline every morning at 7:00 AM IST via `.github/workflows/daily_digest.yml`.
   - **cron-job.org**: Alternatively, set up a free ping to `https://news2u.onrender.com/api/cron/run` every morning.
   - **Manual Browser Test**: Visit `https://news2u.onrender.com/api/cron/run` in your browser anytime to test sending digests!

*(If you ever want Render's native paid cron job instead, simply uncomment the cron block in `render.yaml` with `plan: starter`).*

---

## 🚀 How to Deploy on Render

### Step 1: In the Render Blueprint Setup Screen
- **Blueprint Name**: Enter **`news2u`** (or `news2u-app`)
- **Branch**: `main`
- **Blueprint Path**: `render.yaml` (default)
- Click **Apply**.
  Render will provision:
  - **`news2u-db`** (PostgreSQL Database - Free)
  - **`news2u`** (Web Service - Free)

### Step 2: Set Environment Variables
In the Render dashboard under `news2u` → **Environment**, provide:
- `GEMINI_API_KEY`: Your Gemini API key from [Google AI Studio](https://aistudio.google.com).
- `GEMINI_MODEL`: `gemini-2.5-flash`
- `MY_EMAIL`: Your Gmail address (sender).
- `APP_PASSWORD`: Your 16-character Google App Password from [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
- `USER_NAME`: Your name (e.g. `Sanjay`).

---

## 🌐 Public URL
Once deployed, your live landing page will be at:
**`https://news2u.onrender.com`**

Share this URL with anyone so they can subscribe and rank their AI news priorities!
