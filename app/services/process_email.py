import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.agent.curator_agent import CuratorAgent
from app.profiles.user_profile import USER_PROFILE
from app.database.repository import Repository
from app.services.email import send_email, digest_to_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def normalize_source_name(source: str) -> str:
    """Normalize user-entered source labels to standard article_type."""
    s = (source or "").strip().lower()
    if s in ("openai", "gpt", "chatgpt"):
        return "openai"
    elif s in ("anthropic", "claude"):
        return "anthropic"
    elif s in ("youtube", "video", "videos"):
        return "youtube"
    return s


def rank_digests_by_priority(
    digests: List[Dict[str, Any]],
    priority_1: str = "openai",
    priority_2: str = "anthropic",
    priority_3: str = "youtube",
    curator_scores: Optional[Dict[str, float]] = None,
    top_n: int = 10,
) -> List[RankedArticleDetail]:
    """
    Ranks digests prioritizing the subscriber's custom order (priority_1 -> priority_2 -> priority_3).
    Within each priority tier, articles are ordered by LLM curator relevance score and recency.
    """
    curator_scores = curator_scores or {}

    p1 = normalize_source_name(priority_1)
    p2 = normalize_source_name(priority_2)
    p3 = normalize_source_name(priority_3)

    def get_tier(article_type: str) -> int:
        norm = normalize_source_name(article_type)
        if norm == p1:
            return 1
        elif norm == p2:
            return 2
        elif norm == p3:
            return 3
        return 4

    # Group digests into priority buckets
    tier_map: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    for d in digests:
        tier = get_tier(d.get("article_type", ""))
        tier_map[tier].append(d)

    # Sort each tier by curator relevance score (descending), then created_at (descending)
    def sort_key(item: Dict[str, Any]):
        score = curator_scores.get(item["id"], 8.0)
        created = item.get("created_at")
        ts = created.timestamp() if isinstance(created, datetime) else 0.0
        return (score, ts)

    for tier in (1, 2, 3, 4):
        tier_map[tier].sort(key=sort_key, reverse=True)

    # Assemble candidate list: priority 1 leads, followed by 2, 3, and others
    ordered_digests = tier_map[1] + tier_map[2] + tier_map[3] + tier_map[4]
    selected_digests = ordered_digests[:top_n]

    source_labels = {
        "openai": "OpenAI / GPT Research",
        "anthropic": "Anthropic / Claude",
        "youtube": "Curated YouTube Video",
    }

    ranked_articles = []
    for idx, d in enumerate(selected_digests):
        score = curator_scores.get(d["id"], 8.5)
        src_label = source_labels.get(d.get("article_type", ""), d.get("article_type", "").title())
        tier = get_tier(d.get("article_type", ""))
        reasoning = (
            f"Top Priority match ({src_label})"
            if tier == 1
            else f"Secondary Priority match ({src_label})"
            if tier == 2
            else f"Curated AI highlight ({src_label})"
        )

        ranked_articles.append(
            RankedArticleDetail(
                digest_id=d["id"],
                rank=idx + 1,
                relevance_score=score,
                reasoning=reasoning,
                title=d.get("title", "Untitled Update"),
                summary=d.get("summary", ""),
                url=d.get("url", ""),
                article_type=d.get("article_type", ""),
            )
        )

    return ranked_articles


def generate_personalized_digest(
    subscriber_name: str,
    priority_1: str,
    priority_2: str,
    priority_3: str,
    digests: List[Dict[str, Any]],
    curator_scores: Optional[Dict[str, float]] = None,
    top_n: int = 10,
) -> EmailDigestResponse:
    """Generates an EmailDigestResponse tailored for a specific subscriber."""
    ranked_articles = rank_digests_by_priority(
        digests=digests,
        priority_1=priority_1,
        priority_2=priority_2,
        priority_3=priority_3,
        curator_scores=curator_scores,
        top_n=top_n,
    )

    email_agent = EmailAgent(user_profile={"name": subscriber_name})
    return email_agent.create_email_digest_response(
        ranked_articles=ranked_articles,
        total_ranked=len(ranked_articles),
        limit=top_n,
    )


def generate_email_digest(hours: int = 24, top_n: int = 10) -> EmailDigestResponse:
    """Backward-compatible single-user generator using default USER_PROFILE."""
    repo = Repository()
    digests = repo.get_recent_digests(hours=hours)
    if not digests:
        raise ValueError("No digests available")

    curator = CuratorAgent(USER_PROFILE)
    curator_scores = {}
    try:
        ranked = curator.rank_digests(digests)
        for r in ranked:
            curator_scores[r.digest_id] = r.relevance_score
    except Exception as e:
        logger.warning(f"Curator ranking fallback: {e}")

    return generate_personalized_digest(
        subscriber_name=USER_PROFILE.get("name", "Curator"),
        priority_1="openai",
        priority_2="anthropic",
        priority_3="youtube",
        digests=digests,
        curator_scores=curator_scores,
        top_n=top_n,
    )


def send_digest_email(hours: int = 24, top_n: int = 10) -> dict:
    """
    Sends personalized daily digests to all active subscribers.
    If no subscribers are in the database, falls back to RECIPIENT_EMAIL / MY_EMAIL.
    """
    repo = Repository()
    digests = repo.get_recent_digests(hours=hours, exclude_sent=True)

    if not digests:
        logger.info(f"No unsent digests found in {hours}h window. Fetching latest available digests...")
        digests = repo.get_recent_digests(hours=720, exclude_sent=False)

    # If database truly has 0 digests, generate them immediately from undigested articles
    if not digests:
        logger.info("No digests in database at all. Processing undigested articles immediately...")
        from app.services.process_digest import process_digests
        process_digests(limit=10)
        digests = repo.get_recent_digests(hours=720, exclude_sent=False)

    if not digests:
        logger.warning("No digests exist in database at all yet.")
        return {
            "success": False,
            "skipped": True,
            "message": "No digests available to send",
            "articles_count": 0,
            "subscribers_sent": 0,
            "subscribers_failed": 0,
        }

    # Pre-compute curator scores once per batch
    curator_scores = {}
    try:
        curator = CuratorAgent(USER_PROFILE)
        ranked = curator.rank_digests(digests)
        for r in ranked:
            curator_scores[r.digest_id] = r.relevance_score
    except Exception as e:
        logger.warning(f"Batch curator scoring skipped or encountered error: {e}")

    # Fetch all registered active subscribers
    subscribers = repo.get_active_subscribers()

    # Fallback to single-user environment recipient if database has no subscribers yet
    if not subscribers:
        fallback_email = os.getenv("RECIPIENT_EMAIL") or os.getenv("MY_EMAIL") or "qwertysudheer60@gmail.com"

        class FallbackSubscriber:
            name = os.getenv("USER_NAME", "Sanjay")
            email = fallback_email
            priority_1 = "openai"
            priority_2 = "anthropic"
            priority_3 = "youtube"

        subscribers = [FallbackSubscriber()]
        logger.info(f"No database subscribers found. Falling back to default recipient: {fallback_email}")

    logger.info(f"Dispatching personalized digests to {len(subscribers)} subscriber(s)...")

    sent_count = 0
    failed_count = 0
    all_sent_digest_ids = set()

    for sub in subscribers:
        try:
            logger.info(
                f"Preparing personalized digest for {sub.name} <{sub.email}> "
                f"[Priorities: 1={sub.priority_1}, 2={sub.priority_2}, 3={sub.priority_3}]"
            )

            digest_response = generate_personalized_digest(
                subscriber_name=sub.name,
                priority_1=sub.priority_1,
                priority_2=sub.priority_2,
                priority_3=sub.priority_3,
                digests=digests,
                curator_scores=curator_scores,
                top_n=top_n,
            )

            markdown_content = digest_response.to_markdown()
            html_content = digest_to_html(digest_response)

            # Save preview locally for debugging
            try:
                with open("latest_ai_news_preview.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            except Exception:
                pass

            date_str = datetime.now().strftime("%B %d, %Y")
            subject = f"NEWS2U | Daily AI News Digest - {date_str}"

            send_email(
                subject=subject,
                body_text=markdown_content,
                body_html=html_content,
                recipients=[sub.email],
            )

            for art in digest_response.articles:
                all_sent_digest_ids.add(art.digest_id)

            sent_count += 1
            logger.info(f"Digest successfully delivered to {sub.email}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to deliver digest to {sub.email}: {e}")

    # Mark all successfully included digests as sent
    if all_sent_digest_ids:
        repo.mark_digests_as_sent(list(all_sent_digest_ids))
        logger.info(f"Marked {len(all_sent_digest_ids)} digests as sent in database.")

    return {
        "success": sent_count > 0,
        "subscribers_sent": sent_count,
        "subscribers_failed": failed_count,
        "articles_count": len(all_sent_digest_ids) or len(digests[:top_n]),
    }


if __name__ == "__main__":
    result = send_digest_email(hours=24, top_n=10)
    print("\n=== Multi-Subscriber Dispatch Summary ===")
    print(f"Subscribers Sent: {result.get('subscribers_sent', 0)}")
    print(f"Subscribers Failed: {result.get('subscribers_failed', 0)}")
    print(f"Total Unique Articles Included: {result.get('articles_count', 0)}")
