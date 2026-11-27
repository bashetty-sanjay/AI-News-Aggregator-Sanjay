from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import YouTubeVideo, OpenAIArticle, AnthropicArticle, Digest, Subscriber
from .connection import get_session


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def _bulk_create_items(
        self,
        items: List[dict],
        model_class,
        id_field: str,
        id_attr: str,
    ) -> int:
        new_items = []
        for item in items:
            existing = (
                self.session.query(model_class)
                .filter_by(**{id_attr: item[id_field]})
                .first()
            )
            if not existing:
                new_items.append(model_class(**item))
        if new_items:
            self.session.add_all(new_items)
            self.session.commit()
        return len(new_items)

    def create_youtube_video(
        self,
        video_id: str,
        title: str,
        url: str,
        channel_id: str,
        published_at: datetime,
        description: str = "",
        transcript: Optional[str] = None,
    ) -> Optional[YouTubeVideo]:
        existing = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if existing:
            return None
        video = YouTubeVideo(
            video_id=video_id,
            title=title,
            url=url,
            channel_id=channel_id,
            published_at=published_at,
            description=description,
            transcript=transcript,
        )
        self.session.add(video)
        self.session.commit()
        return video

    def create_openai_article(
        self,
        guid: str,
        title: str,
        url: str,
        published_at: datetime,
        description: str = "",
        category: Optional[str] = None,
    ) -> Optional[OpenAIArticle]:
        existing = self.session.query(OpenAIArticle).filter_by(guid=guid).first()
        if existing:
            return None
        article = OpenAIArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category,
        )
        self.session.add(article)
        self.session.commit()
        return article

    def create_anthropic_article(
        self,
        guid: str,
        title: str,
        url: str,
        published_at: datetime,
        description: str = "",
        category: Optional[str] = None,
    ) -> Optional[AnthropicArticle]:
        existing = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if existing:
            return None
        article = AnthropicArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category,
        )
        self.session.add(article)
        self.session.commit()
        return article

    def bulk_create_youtube_videos(self, videos: List[dict]) -> int:
        formatted_videos = [
            {
                "video_id": v["video_id"],
                "title": v["title"],
                "url": v["url"],
                "channel_id": v.get("channel_id", ""),
                "published_at": v["published_at"],
                "description": v.get("description", ""),
                "transcript": v.get("transcript"),
            }
            for v in videos
        ]
        return self._bulk_create_items(
            formatted_videos, YouTubeVideo, "video_id", "video_id"
        )

    def bulk_create_openai_articles(self, articles: List[dict]) -> int:
        formatted_articles = [
            {
                "guid": a["guid"],
                "title": a["title"],
                "url": a["url"],
                "published_at": a["published_at"],
                "description": a.get("description", ""),
                "category": a.get("category"),
            }
            for a in articles
        ]
        return self._bulk_create_items(
            formatted_articles, OpenAIArticle, "guid", "guid"
        )

    def bulk_create_anthropic_articles(self, articles: List[dict]) -> int:
        formatted_articles = [
            {
                "guid": a["guid"],
                "title": a["title"],
                "url": a["url"],
                "published_at": a["published_at"],
                "description": a.get("description", ""),
                "category": a.get("category"),
            }
            for a in articles
        ]
        return self._bulk_create_items(
            formatted_articles, AnthropicArticle, "guid", "guid"
        )

    def get_anthropic_articles_without_markdown(
        self, limit: Optional[int] = None
    ) -> List[AnthropicArticle]:
        query = self.session.query(AnthropicArticle).filter(
            AnthropicArticle.markdown.is_(None)
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def update_anthropic_article_markdown(self, guid: str, markdown: Any) -> bool:
        try:
            article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
            if article:
                clean_md = (
                    str(markdown.text_content)
                    if hasattr(markdown, "text_content")
                    else str(markdown or "")
                )
                article.markdown = clean_md
                self.session.commit()
                return True
            return False
        except Exception:
            self.session.rollback()
            return False

    def get_youtube_videos_without_transcript(
        self, limit: Optional[int] = None
    ) -> List[YouTubeVideo]:
        query = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.transcript.is_(None)
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def update_youtube_video_transcript(self, video_id: str, transcript: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if video:
            video.transcript = transcript
            self.session.commit()
            return True
        return False

    def get_articles_without_digest(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        articles = []
        seen_ids = set()

        digests = self.session.query(Digest).all()
        for d in digests:
            seen_ids.add(f"{d.article_type}:{d.article_id}")

        youtube_videos = self.session.query(YouTubeVideo).all()
        for video in youtube_videos:
            key = f"youtube:{video.video_id}"
            if key not in seen_ids:
                content = (
                    video.transcript
                    if (video.transcript and video.transcript != "__UNAVAILABLE__")
                    else (video.description or video.title)
                )
                articles.append(
                    {
                        "type": "youtube",
                        "id": video.video_id,
                        "title": video.title,
                        "url": video.url,
                        "content": content,
                        "published_at": video.published_at,
                    }
                )

        openai_articles = self.session.query(OpenAIArticle).all()
        for article in openai_articles:
            key = f"openai:{article.guid}"
            if key not in seen_ids:
                articles.append(
                    {
                        "type": "openai",
                        "id": article.guid,
                        "title": article.title,
                        "url": article.url,
                        "content": article.description or article.title,
                        "published_at": article.published_at,
                    }
                )

        anthropic_articles = self.session.query(AnthropicArticle).all()
        for article in anthropic_articles:
            key = f"anthropic:{article.guid}"
            if key not in seen_ids:
                articles.append(
                    {
                        "type": "anthropic",
                        "id": article.guid,
                        "title": article.title,
                        "url": article.url,
                        "content": article.markdown or article.description or article.title,
                        "published_at": article.published_at,
                    }
                )

        if limit:
            articles = articles[:limit]

        return articles

    def create_digest(
        self,
        article_type: str,
        article_id: str,
        url: str,
        title: str,
        summary: str,
        published_at: Optional[datetime] = None,
    ) -> Optional[Digest]:
        digest_id = f"{article_type}:{article_id}"
        existing = self.session.query(Digest).filter_by(id=digest_id).first()
        if existing:
            return None

        digest = Digest(
            id=digest_id,
            article_type=article_type,
            article_id=article_id,
            url=url,
            title=title,
            summary=summary,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(digest)
        self.session.commit()
        return digest

    def get_recent_digests(
        self, hours: int = 24, exclude_sent: bool = True
    ) -> List[Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = self.session.query(Digest).filter(Digest.created_at >= cutoff_time)

        if exclude_sent:
            query = query.filter(Digest.sent_at.is_(None))

        digests = query.order_by(Digest.created_at.desc()).all()

        # If no unsent digests found in narrow window, search wider (30 days) of unsent digests
        if not digests and hours < 720:
            wide_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            wide_query = self.session.query(Digest).filter(Digest.created_at >= wide_cutoff)
            if exclude_sent:
                wide_query = wide_query.filter(Digest.sent_at.is_(None))
            digests = wide_query.order_by(Digest.created_at.desc()).all()

        # If STILL no unsent digests, fallback to latest digests (even if previously sent,
        # ensuring subscribers always receive a high-value daily digest)
        if not digests:
            digests = self.session.query(Digest).order_by(Digest.created_at.desc()).limit(15).all()

        return [
            {
                "id": d.id,
                "article_type": d.article_type,
                "article_id": d.article_id,
                "url": d.url,
                "title": d.title,
                "summary": d.summary,
                "created_at": d.created_at,
                "sent_at": d.sent_at,
            }
            for d in digests
        ]

    def mark_digests_as_sent(self, digest_ids: List[str]) -> int:
        sent_time = datetime.now(timezone.utc)
        updated = (
            self.session.query(Digest)
            .filter(Digest.id.in_(digest_ids))
            .update({Digest.sent_at: sent_time}, synchronize_session=False)
        )
        self.session.commit()
        return updated

    # ==========================================
    # Subscriber Management
    # ==========================================

    def create_or_update_subscriber(
        self,
        name: str,
        email: str,
        priority_1: str = "openai",
        priority_2: str = "anthropic",
        priority_3: str = "youtube",
    ) -> Subscriber:
        """Create a new subscriber or update priorities if already registered."""
        clean_email = email.strip().lower()
        clean_name = name.strip() or clean_email.split("@")[0]

        existing = (
            self.session.query(Subscriber)
            .filter(Subscriber.email == clean_email)
            .first()
        )

        if existing:
            existing.name = clean_name
            existing.priority_1 = priority_1.strip().lower()
            existing.priority_2 = priority_2.strip().lower()
            existing.priority_3 = priority_3.strip().lower()
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return existing

        subscriber = Subscriber(
            name=clean_name,
            email=clean_email,
            priority_1=priority_1.strip().lower(),
            priority_2=priority_2.strip().lower(),
            priority_3=priority_3.strip().lower(),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(subscriber)
        self.session.commit()
        return subscriber

    def get_active_subscribers(self) -> List[Subscriber]:
        """Retrieve all active subscribers."""
        return (
            self.session.query(Subscriber)
            .filter(Subscriber.is_active.is_(True))
            .order_by(Subscriber.created_at.asc())
            .all()
        )

    def get_subscriber_by_email(self, email: str) -> Optional[Subscriber]:
        """Find a subscriber by email address."""
        clean_email = email.strip().lower()
        return (
            self.session.query(Subscriber)
            .filter(Subscriber.email == clean_email)
            .first()
        )

    def unsubscribe(self, email: str) -> bool:
        """Deactivate a subscriber."""
        clean_email = email.strip().lower()
        sub = (
            self.session.query(Subscriber)
            .filter(Subscriber.email == clean_email)
            .first()
        )
        if sub:
            sub.is_active = False
            sub.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return True
        return False
