import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Windows UTF-8 console compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

from app.scrapers.openai import OpenAIScraper
from app.scrapers.anthropic import AnthropicScraper
from app.scrapers.youtube import YouTubeScraper
from app.config import YOUTUBE_CHANNELS
from app.services.email import send_email


def build_news_digest_html(articles: list, recipient_name: str = "Sudheer") -> str:
    """Builds a rich, responsive HTML email digest for latest AI news."""
    date_str = datetime.now().strftime("%B %d, %Y")

    cards_html = []
    for idx, item in enumerate(articles, 1):
        source = item.get("source", "AI News")
        title = item.get("title", "Untitled")
        url = item.get("url", "#")
        desc = item.get("description", "No description available.")
        pub = item.get("published_at")
        pub_str = pub.strftime("%b %d, %Y") if hasattr(pub, "strftime") else str(pub or "")

        # Source badge color
        badge_color = "#10a37f" if "OpenAI" in source else ("#cc785c" if "Anthropic" in source else "#ff0000")

        card = f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <span style="background-color: {badge_color}; color: #ffffff; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 3px 10px; border-radius: 20px;">
                    {source}
                </span>
                <span style="color: #64748b; font-size: 12px;">{pub_str}</span>
            </div>
            <h3 style="margin: 0 0 10px 0; font-size: 18px; line-height: 1.4; color: #0f172a;">
                <a href="{url}" style="color: #0f172a; text-decoration: none; font-weight: 600;" target="_blank">
                    {title}
                </a>
            </h3>
            <p style="margin: 0 0 14px 0; color: #334155; font-size: 14px; line-height: 1.6;">
                {desc[:400] + ('...' if len(desc) > 400 else '')}
            </p>
            <a href="{url}" style="display: inline-block; color: #2563eb; font-size: 13px; font-weight: 600; text-decoration: none;" target="_blank">
                Read full update &rarr;
            </a>
        </div>
        """
        cards_html.append(card)

    articles_section = "\n".join(cards_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily AI News Digest</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 30px 15px; color: #0f172a;">
    <div style="max-width: 640px; margin: 0 auto;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; padding: 28px; color: #ffffff; margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #38bdf8; margin-bottom: 8px;">
                AI Intelligence Digest &bull; {date_str}
            </div>
            <h1 style="margin: 0 0 10px 0; font-size: 26px; font-weight: 700; line-height: 1.2;">
                Hello {recipient_name}, here is your latest AI News Update
            </h1>
            <p style="margin: 0; color: #94a3b8; font-size: 15px; line-height: 1.5;">
                We aggregated the most significant breakthroughs, research, and releases from top AI labs and creators.
            </p>
        </div>

        <!-- Articles List -->
        <div>
            {articles_section}
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 30px; padding: 20px; color: #64748b; font-size: 12px; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0;">Recipient: {os.getenv('RECIPIENT_EMAIL') or os.getenv('MY_EMAIL', 'Configured Email')}</p>
        </div>
    </div>
</body>
</html>"""


def build_news_digest_markdown(articles: list, recipient_name: str = "Sudheer") -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    lines = [
        f"# Daily AI News Digest - {date_str}",
        f"\nHello {recipient_name}, here is your latest AI news update:\n",
    ]
    for item in articles:
        lines.append(f"## [{item.get('source', 'AI')}] {item.get('title')}")
        lines.append(f"Published: {item.get('published_at', '')}")
        lines.append(f"{item.get('description', '')[:300]}")
        lines.append(f"[Read full article]({item.get('url')})\n---")
    return "\n\n".join(lines)


def fetch_latest_news(hours: int = 168, max_items: int = 6) -> list:
    """Fetches real articles from OpenAI, Anthropic, and YouTube RSS feeds."""
    print(f"[*] Scraping latest AI news from sources (last {hours} hours)...")
    articles = []

    # 1. OpenAI
    try:
        openai_scraper = OpenAIScraper()
        o_articles = openai_scraper.get_articles(hours=hours)
        for a in o_articles:
            articles.append({
                "source": "OpenAI",
                "title": a.title,
                "url": a.url,
                "description": a.description,
                "published_at": a.published_at,
            })
        print(f"  [OK] Found {len(o_articles)} OpenAI articles")
    except Exception as e:
        print(f"  [WARN] OpenAI scraper: {e}")

    # 2. Anthropic
    try:
        anthropic_scraper = AnthropicScraper()
        a_articles = anthropic_scraper.get_articles(hours=hours)
        for a in a_articles:
            articles.append({
                "source": "Anthropic",
                "title": a.title,
                "url": a.url,
                "description": a.description,
                "published_at": a.published_at,
            })
        print(f"  [OK] Found {len(a_articles)} Anthropic articles")
    except Exception as e:
        print(f"  [WARN] Anthropic scraper: {e}")

    # 3. YouTube
    try:
        yt_scraper = YouTubeScraper()
        for channel_id in YOUTUBE_CHANNELS:
            v_articles = yt_scraper.get_latest_videos(channel_id, hours=hours)
            for v in v_articles:
                articles.append({
                    "source": "YouTube AI",
                    "title": v.title,
                    "url": v.url,
                    "description": v.description,
                    "published_at": v.published_at,
                })
            print(f"  [OK] Found {len(v_articles)} YouTube videos from channel {channel_id}")
    except Exception as e:
        print(f"  [WARN] YouTube scraper: {e}")

    # Sort descending by published_at
    articles.sort(
        key=lambda x: x["published_at"] if hasattr(x["published_at"], "timestamp") else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    return articles[:max_items]


def main():
    sender = os.getenv("MY_EMAIL")
    recipient = os.getenv("RECIPIENT_EMAIL") or sender
    app_password = os.getenv("APP_PASSWORD")
    user_name = os.getenv("USER_NAME", "AI Enthusiast")

    if not sender or not recipient:
        print("[ERROR] MY_EMAIL or RECIPIENT_EMAIL is not configured in .env file.")
        print("Please configure your email address in .env before sending.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("   AI News Aggregator - Email Dispatch & Update Tool")
    print("=" * 65)
    print(f"Sender (MY_EMAIL):       {sender}")
    print(f"Recipient (RECIPIENT):   {recipient}")
    print(f"App Password Configured: {'YES' if app_password else 'NO (Required for Gmail delivery)'}")
    print("=" * 65 + "\n")

    # 1. Fetch latest real AI news
    news_items = fetch_latest_news(hours=168, max_items=6)
    if not news_items:
        print("[!] No recent articles found in the last 7 days. Widening search window...")
        news_items = fetch_latest_news(hours=720, max_items=6)

    if not news_items:
        print("[!] No articles found. Creating fallback summary.")
        news_items = [{
            "source": "AI Aggregator",
            "title": "AI News Aggregator Pipeline Initialized",
            "url": "https://openai.com/news",
            "description": "Your AI News Aggregator system is ready and configured. Scrapers and delivery agents are operational.",
            "published_at": datetime.now(timezone.utc),
        }]

    print(f"\n[*] Preparing AI news digest with {len(news_items)} top updates...")

    # 2. Build email content
    html_content = build_news_digest_html(news_items, recipient_name=user_name)
    markdown_content = build_news_digest_markdown(news_items, recipient_name=user_name)
    subject = f"Latest AI News Digest for {user_name} - {datetime.now().strftime('%B %d, %Y')}"

    # Always save a local preview file
    preview_file = "latest_ai_news_preview.html"
    try:
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[OK] Local HTML preview generated: {preview_file}")
    except Exception as e:
        print(f"[WARN] Could not save preview: {e}")

    # 3. Attempt email dispatch via Gmail SMTP
    if not app_password:
        print("\n" + "!" * 65)
        print("ACTION REQUIRED TO DELIVER TO GMAIL INBOX:")
        print("Google requires a 16-character 'App Password' for Gmail SMTP.")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("   (Ensure 2-Step Verification is turned ON in your Google Account)")
        print("2. Enter App Name: 'AI News Aggregator'")
        print("3. Click 'Create' and copy the 16-character password (e.g., 'abcd efgh ijkl mnop')")
        print("4. Add it to your .env file:")
        print("     APP_PASSWORD=your_16_character_app_password")
        print("5. Run this command again:")
        print("     uv run python send_news_update.py")
        print("!" * 65)
        return

    print(f"\n[*] Sending email to {recipient} via Gmail SMTP...")
    try:
        send_email(
            subject=subject,
            body_text=markdown_content,
            body_html=html_content,
            recipients=[recipient],
        )
        print("\n" + "=" * 65)
        print(f"[SUCCESS] Email successfully delivered to {recipient}!")
        print(f"Subject: {subject}")
        print(f"Articles included: {len(news_items)}")
        print("=" * 65)
    except Exception as e:
        print(f"\n[ERROR] Failed to send email: {e}")
        print("\nChecklist:")
        print("1. Is 2-Step Verification enabled on your Google Account?")
        print("2. Did you generate an App Password from https://myaccount.google.com/apppasswords ?")
        print("3. Is APP_PASSWORD set properly in .env without extra spaces?")
        sys.exit(1)


if __name__ == "__main__":
    main()
