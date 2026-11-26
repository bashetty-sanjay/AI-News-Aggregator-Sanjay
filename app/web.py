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


@app.get("/api/cron/run")
@app.post("/api/cron/run")
async def trigger_cron_pipeline(secret: Optional[str] = None):
    """
    Trigger the daily scraping, ranking, and email pipeline.
    Can be called manually from browser, via cron-job.org, or via GitHub Actions.
    """
    expected_secret = os.getenv("CRON_SECRET")
    if expected_secret and secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    try:
        import asyncio
        from app.daily_runner import run_daily_pipeline
        result = await asyncio.to_thread(run_daily_pipeline, hours=24, top_n=10)
        return {
            "success": True,
            "message": "Daily digest pipeline executed successfully",
            "result": result,
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
    uvicorn.run("app.web:app", host="0.0.0.0", port=port, reload=True)
