# Deployment Guide: Render.com

This guide walks you through deploying the AI News Aggregator to Render.com with PostgreSQL and scheduled daily execution.

## Prerequisites

- Render.com account (sign up at https://render.com)
- GitHub account with this repository
- OpenAI API key
- Gmail account with app password (for email sending)

## Step-by-Step Deployment

### 1. Create Render Account

1. Go to https://render.com
2. Sign up for a free account (or log in if you already have one)
3. Verify your email address

### 2. Connect GitHub Repository

1. In Render dashboard, click "New" → "Blueprint"
2. Connect your GitHub account if not already connected
3. Select the repository: `ai-news-aggregator`
4. Select the branch: `deployment` (or `master` if you merge)
5. Render will detect `render.yaml` automatically

### 3. Review Blueprint Configuration

Render will read `render.yaml` and show you:
- **PostgreSQL Database**: `ai-news-aggregator-db`
- **Cron Job**: `daily-digest-job` (runs daily at midnight UTC)

Click "Apply" to create these services.

### 4. Set Environment Variables

After services are created, you need to set environment variables for the cron job:

1. Go to the `daily-digest-job` service in Render dashboard
2. Navigate to "Environment" tab
3. Add the following variables:

```
OPENAI_API_KEY=your_openai_api_key_here
MY_EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password_here
```

**Note**: `DATABASE_URL` is automatically set by Render - you don't need to add it manually.

### 5. Initialize Database

The database tables will be created automatically when the cron job runs for the first time (via `app.database.create_tables` in the Dockerfile).

Alternatively, you can manually trigger table creation:

1. Go to the cron job service
2. Click "Manual Deploy" → "Deploy latest commit"
3. Or wait for the scheduled run

### 6. Verify Deployment

1. Check the cron job logs in Render dashboard
2. Look for successful execution messages
3. Verify email was sent (check your inbox)

### 7. Adjust Schedule (Optional)

To change when the daily digest runs:

1. Edit `render.yaml`:
   ```yaml
   schedule: "0 8 * * *"  # 8 AM UTC instead of midnight
   ```
2. Push changes to GitHub
3. Render will automatically update

**Cron Schedule Format**: `minute hour day month weekday`
- `0 0 * * *` = Daily at midnight UTC
- `0 8 * * *` = Daily at 8 AM UTC
- `0 0 * * 1` = Every Monday at midnight UTC

## Environment Variables Reference

| Variable | Required | Description | Where to Set |
|----------|----------|-------------|--------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | Auto-set by Render |
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM | Render dashboard |
| `MY_EMAIL` | Yes | Gmail address for sending | Render dashboard |
| `APP_PASSWORD` | Yes | Gmail app password | Render dashboard |

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is set (should be automatic)
- Check database service is running
- Verify network connectivity between services

### Cron Job Not Running

- Check cron job logs in Render dashboard
- Verify schedule syntax in `render.yaml`
- Ensure Docker build succeeded

### Email Not Sending

- Verify `MY_EMAIL` and `APP_PASSWORD` are correct
- Check Gmail app password is valid (not regular password)
- Review email service logs for errors

### Build Failures

- Check Dockerfile syntax
- Verify all dependencies in `pyproject.toml`
- Review build logs for specific errors

## Local Development

For local development, use docker-compose:

```bash
cd docker
docker compose up -d
```

This starts PostgreSQL locally. Set environment variables in `.env` file (copy from `app/example.env`).

## Updating the Deployment

1. Make changes to code
2. Commit and push to GitHub
3. Render automatically rebuilds and redeploys
4. For cron jobs, changes take effect on next scheduled run

## Cost Considerations

**Free Tier Limits:**
- PostgreSQL: 90 days retention, 1GB storage
- Cron jobs: Limited execution time

**Recommended for Production:**
- Upgrade to Starter plan ($7/month) for PostgreSQL
- Ensures data persistence and better performance

## Monitoring

- **Logs**: View in Render dashboard under each service
- **Database**: Check connection count and storage usage
- **Cron Jobs**: Monitor execution history and success rate

## Support

- Render Documentation: https://render.com/docs
- Render Support: Available in dashboard
- Project Issues: Check GitHub repository issues

