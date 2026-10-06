import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

from app.database.connection import get_session, get_database_info
from app.database.models import OpenAIArticle, AnthropicArticle, YouTubeVideo, Digest


def display_table(title: str, items: list, headers: list, formatter):
    print("\n" + "=" * 70)
    print(f" {title} (Total: {len(items)})")
    print("=" * 70)
    if not items:
        print("  (No records found yet)")
        return
    for idx, item in enumerate(items, 1):
        formatter(idx, item)


def main():
    info = get_database_info()
    print("\n" + "#" * 70)
    print(f"  AI NEWS AGGREGATOR - DATABASE INSPECTOR")
    print(f"  Database Engine: {info['host']} ({info['environment']})")
    print(f"  Storage URL:     {info['url_masked']}")
    print("#" * 70)

    try:
        session = get_session()

        # 1. Digests
        digests = session.query(Digest).order_by(Digest.created_at.desc()).limit(10).all()
        def format_digest(idx, d):
            status = f"Sent at {d.sent_at.strftime('%Y-%m-%d %H:%M')}" if d.sent_at else "Pending send"
            print(f"[{idx}] {d.title}")
            print(f"    Type: {d.article_type} | Status: {status}")
            print(f"    URL:  {d.url}")
            print(f"    Summary: {d.summary[:150]}...")
            print("-" * 70)
        display_table("RECENT DIGESTS (Summarized by Gemini/AI)", digests, [], format_digest)

        # 2. OpenAI Articles
        openai_articles = session.query(OpenAIArticle).order_by(OpenAIArticle.published_at.desc()).limit(5).all()
        def format_openai(idx, a):
            print(f"[{idx}] {a.title}")
            print(f"    Published: {a.published_at.strftime('%Y-%m-%d')} | Category: {a.category or 'General'}")
            print(f"    URL:       {a.url}")
            print("-" * 70)
        display_table("OPENAI ARTICLES (Scraped from RSS)", openai_articles, [], format_openai)

        # 3. Anthropic Articles
        anthropic_articles = session.query(AnthropicArticle).order_by(AnthropicArticle.published_at.desc()).limit(5).all()
        def format_anthropic(idx, a):
            print(f"[{idx}] {a.title}")
            print(f"    Published: {a.published_at.strftime('%Y-%m-%d')}")
            print(f"    URL:       {a.url}")
            print("-" * 70)
        display_table("ANTHROPIC ARTICLES (Scraped from RSS)", anthropic_articles, [], format_anthropic)

        # 4. YouTube Videos
        yt_videos = session.query(YouTubeVideo).order_by(YouTubeVideo.published_at.desc()).limit(5).all()
        def format_yt(idx, v):
            has_transcript = "Yes" if v.transcript else "No"
            print(f"[{idx}] {v.title}")
            print(f"    Published: {v.published_at.strftime('%Y-%m-%d')} | Transcript Loaded: {has_transcript}")
            print(f"    URL:       {v.url}")
            print("-" * 70)
        display_table("YOUTUBE VIDEOS (Scraped from Channels)", yt_videos, [], format_yt)

    except Exception as e:
        print(f"\n[ERROR] Could not read database: {e}")
        print("\nTip: If you're using Docker, make sure Docker Desktop is open and run:")
        print("     docker compose up -d postgres")
        print("Or if running locally without Docker, set USE_SQLITE=true in your .env file.")


if __name__ == "__main__":
    main()
