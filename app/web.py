import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.database.connection import engine, get_database_info
from app.database.models import Base
from app.database.repository import Repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Ensure all database tables exist on startup
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.warning(f"Database initialization deferred or failed: {e}")

app = FastAPI(
    title="NEWS2U - AI News Digest",
    description="NEWS2U: Automated multi-source AI news aggregator and personalized daily briefing",
    version="1.0.0",
)

# Allow CORS for development and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"


class SubscribeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    priority_1: str = Field(default="openai")
    priority_2: str = Field(default="anthropic")
    priority_3: str = Field(default="youtube")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, clean):
            raise ValueError("Please provide a valid email address.")
        return clean

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty.")
        return cleaned


class UnsubscribeRequest(BaseModel):
    email: str


@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    """Serves the executive Dark Charcoal & Amber Gold landing page."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Landing page template (index.html) not found.",
        )
    html_content = TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint for Render and uptime monitoring."""
    db_info = get_database_info()
    return {
        "status": "healthy",
        "service": "NEWS2U Web",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_info,
    }


@app.post("/api/subscribe")
async def subscribe(request: SubscribeRequest):
    """Subscribes a user with their prioritized source preferences."""
    try:
        repo = Repository()

        # Map display labels to canonical source identifiers
        source_mapping = {
            "openai": "openai",
            "gpt": "openai",
            "chatgpt": "openai",
            "anthropic": "anthropic",
            "claude": "anthropic",
            "youtube": "youtube",
            "video": "youtube",
            "videos": "youtube",
        }

        p1 = source_mapping.get(request.priority_1.lower(), "openai")
        p2 = source_mapping.get(request.priority_2.lower(), "anthropic")
        p3 = source_mapping.get(request.priority_3.lower(), "youtube")

        subscriber = repo.create_or_update_subscriber(
            name=request.name,
            email=request.email,
            priority_1=p1,
            priority_2=p2,
            priority_3=p3,
        )

        display_names = {
            "openai": "OpenAI / GPT Research",
            "anthropic": "Anthropic / Claude Updates",
            "youtube": "Curated AI YouTube Videos",
        }

        logger.info(
            f"New subscription registered: {subscriber.email} ({subscriber.name}) "
            f"Priorities: 1={p1}, 2={p2}, 3={p3}"
        )

        return {
            "success": True,
            "message": (
                f"Welcome aboard, {subscriber.name}! Your daily briefing is configured "
                f"with top priority on {display_names.get(p1, p1)}, followed by "
                f"{display_names.get(p2, p2)} and {display_names.get(p3, p3)}."
            ),
            "subscriber": {
                "name": subscriber.name,
                "email": subscriber.email,
                "priority_1": subscriber.priority_1,
                "priority_2": subscriber.priority_2,
                "priority_3": subscriber.priority_3,
            },
        }
    except Exception as e:
        logger.error(f"Subscription error for {request.email}: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "error": str(e)},
        )


@app.post("/api/unsubscribe")
async def unsubscribe(request: UnsubscribeRequest):
    """Allows a user to unsubscribe from daily briefings."""
    try:
        repo = Repository()
        success = repo.unsubscribe(request.email)
        if success:
            logger.info(f"Subscriber deactivated: {request.email}")
            return {
                "success": True,
                "message": f"{request.email} has been unsubscribed from the daily digest.",
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "Email address not found in active subscribers."},
            )
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)},
        )


@app.get("/api/subscribers")
async def list_subscribers_summary():
    """Summary of active subscribers count and prioritized sources."""
    try:
        repo = Repository()
        subscribers = repo.get_active_subscribers()
        return {
            "total_active": len(subscribers),
            "subscribers": [
                {
                    "name": s.name,
                    "email": f"{s.email[:3]}***@{s.email.split('@')[-1]}",
                    "priority_1": s.priority_1,
                    "priority_2": s.priority_2,
                    "priority_3": s.priority_3,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in subscribers
            ],
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)},
        )


@app.get("/unsubscribe", response_class=HTMLResponse)
async def web_unsubscribe(email: Optional[str] = None):
    """Handles one-click unsubscribe links directly from emails."""
    clean_email = (email or "").strip().lower()
    if clean_email:
        try:
            repo = Repository()
            repo.unsubscribe(clean_email)
            logger.info(f"Unsubscribed via email link: {clean_email}")
        except Exception as e:
            logger.error(f"Error unsubscribing {clean_email}: {e}")

    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribed - NEWS2U</title>
    <style>
        body {{
            background-color: #121316;
            color: #f3f4f6;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            margin: 0;
        }}
        .card {{
            background-color: #1a1c22;
            border: 1px solid #2e323d;
            border-top: 4px solid #f59e0b;
            border-radius: 16px;
            padding: 36px 32px;
            max-width: 460px;
            text-align: center;
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
        }}
        h1 {{ font-size: 22px; color: #ffffff; margin-bottom: 12px; }}
        p {{ color: #9ca3af; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }}
        a {{
            display: inline-block;
            background-color: #f59e0b;
            color: #111318;
            font-weight: 700;
            text-decoration: none;
            padding: 10px 22px;
            border-radius: 8px;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>👋 You've Been Unsubscribed</h1>
        <p><strong>{clean_email}</strong> will no longer receive daily AI news digests from NEWS2U.<br><br>We're sorry to see you go! You can resubscribe anytime.</p>
        <a href="/">← Return to NEWS2U Home</a>
    </div>
</body>
</html>""",
        status_code=200,
    )


@app.get("/api/cron/run")
@app.post("/api/cron/run")
async def trigger_cron_pipeline(secret: Optional[str] = None):
    """
    Trigger the daily scraping, ranking, and email pipeline.
    Can be called manually from browser, via cron-job.org, or via GitHub Actions.
    """
    try:
        import asyncio
        from app.daily_runner import run_daily_pipeline
        result = await asyncio.to_thread(run_daily_pipeline, hours=24, top_n=10)
        email_info = result.get("email", {})
        return {
            "success": True,
            "message": "Daily digest pipeline executed successfully",
            "subscribers_sent": email_info.get("subscribers_sent", 1),
            "articles_count": email_info.get("articles_count", 0),
        }
    except Exception as e:
        logger.error(f"Cron pipeline execution failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.web:app", host="0.0.0.0", port=port, reload=False)
