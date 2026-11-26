# Render Deployment & Architecture Guide

Deploy your multi-user, personalized AI News Aggregator on **Render** in just a few minutes with our unified Blueprint (`render.yaml`).

---

## 🏛 Architecture Overview

When deployed on Render, your system runs as three tightly integrated services:

```
[ Public Subscribers ]
        │
        ▼
┌─────────────────────────────────┐
│   Web Service (FastAPI)         │  --> Serves Dark Charcoal & Amber Gold landing page
│   ai-news-aggregator-web        │  --> Collects Name, Email & 1st/2nd/3rd priorities
└───────────────┬─────────────────┘
                │ saves subscribers
                ▼
┌─────────────────────────────────┐
│   Managed PostgreSQL Database   │  --> Stores articles, transcripts, AI digests & subscribers
│   ai-news-aggregator-db         │
└───────────────▲─────────────────┘
                │ reads & queries
┌───────────────┴─────────────────┐
│   Daily Cron Job                │  --> Runs every morning at 7:00 AM IST (1:30 AM UTC)
│   daily-digest-job              │  --> Scrapes OpenAI, Anthropic, YouTube
│                                 │  --> Curates and tailors digests per subscriber's priorities
│                                 │  --> Dispatches personalized HTML emails via Gmail SMTP
└─────────────────────────────────┘
```

---

## 🚀 Quick Start Deployment (5 Minutes)

### Step 1: Push Code to GitHub
Ensure all recent changes are committed and pushed to your GitHub repository:
```bash
git add .
git commit -m "Add landing page, multi-subscriber priority ranking, and Render blueprint"
git push origin main
```

### Step 2: Deploy Blueprint on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → Select **Blueprint**.
3. Connect your GitHub repository (`AI-News-Aggregator-Sanjay`).
4. Select the `main` branch.
5. Click **Apply**.
   Render will automatically detect `render.yaml` and provision:
   - **PostgreSQL Database** (`ai-news-aggregator-db`)
   - **Web Service** (`ai-news-aggregator-web`)
   - **Daily Cron Job** (`daily-digest-job`)

---

### Step 3: Configure Environment Variables
In the Render dashboard, go to the Environment section for **both** the Web Service and the Cron Job (or set them under an Environment Group):

| Variable | Description | Example |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `MY_EMAIL` | Sender Gmail address | `your.email@gmail.com` |
| `APP_PASSWORD` | 16-character Google App Password | `xxxx yyyy zzzz wwww` |
| `USER_NAME` | Owner / System sender name | `Sanjay` |
| `OPENAI_API_KEY` | (Optional) OpenAI API key for fallback | `sk-proj-...` |
| `DATABASE_URL` | **Auto-configured by Render** | *Do not edit* |

> [!IMPORTANT]
> **Subscribers never enter their Google passwords.**
> Your central server sends all outgoing emails using the credentials above. Subscribers only submit their name, email, and their 3 ranked source priorities.

---

## 🧪 Local Testing

You can run and test everything locally before or after deploying:

### 1. Launch the Frontend & API Server
```bash
uv run uvicorn app.web:app --reload --port 8000
```
Open your browser at **`http://localhost:8000`**:
- View the executive Dark Charcoal & Amber Gold landing page.
- Test subscribing with your email and prioritized sources (e.g. #1 OpenAI, #2 Anthropic, #3 YouTube).
- Health check is live at **`http://localhost:8000/health`**.

### 2. Run the Full Daily Pipeline Manually
```bash
uv run python main.py
```
This will:
1. Ensure all database tables exist (including `subscribers`).
2. Scrape OpenAI, Anthropic, and YouTube sources.
3. Generate digests with Google Gemini.
4. Read active subscribers and their priority preferences.
5. Generate a personalized briefing for each subscriber ordered by their chosen priorities.
6. Deliver the email via Gmail SMTP.

---

## ⏰ Changing the Schedule
To change when the daily briefing sends, edit `schedule` in `render.yaml`:
```yaml
schedule: "30 1 * * *"  # 7:00 AM IST (1:30 AM UTC)
```
For example, for 8:00 AM IST: `schedule: "30 2 * * *"`.
Commit and push to trigger an automatic update on Render.
