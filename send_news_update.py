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

import re
from app.scrapers.openai import OpenAIScraper
from app.scrapers.anthropic import AnthropicScraper
from app.scrapers.youtube import YouTubeScraper
from app.config import YOUTUBE_CHANNELS
from app.services.email import send_email


def get_clean_article_summary(title: str, url: str, raw_desc: str, source: str) -> str:
    """Retrieves AI summary from database or cleans out raw YouTube links and sponsor spam."""
    try:
        from app.database.connection import get_session
        from app.database.models import Digest
        session = get_session()
        d = session.query(Digest).filter(Digest.url == url).first()
        if d and d.summary and len(d.summary) > 25:
            clean_s = d.summary.strip()
            clean_s = re.sub(r"^#+\s*.*$", "", clean_s, flags=re.MULTILINE).strip()
            return clean_s[:380] + ("..." if len(clean_s) > 380 else "")
    except Exception:
        pass

    lines = (raw_desc or "").splitlines()
    clean_lines = []
    for line in lines:
        l = line.strip()
        if not l:
            continue
        if "http://" in l or "https://" in l or "www." in l or ".com" in l:
            continue
        if any(w in l.lower() for w in ["patreon", "discord", "twitter", "instagram", "tiktok", "subscribe", "sponsor", "github.com", "coupon", "merch"]):
            continue
        if re.match(r"^\d{1,2}:\d{2}", l):
            continue
        clean_lines.append(l)

    cleaned = " ".join(clean_lines)
    cleaned = re.sub(r"https?://\S+", "", cleaned).strip()

    if len(cleaned) >= 50:
        return cleaned[:380] + ("..." if len(cleaned) > 380 else "")

    if "youtube" in source.lower():
        return f"This video covers key breakthroughs surrounding '{title}', analyzing hands-on model benchmarks, technical capabilities, and developer workflow implementations."

    return raw_desc[:380] if raw_desc else "Latest curated updates and research breakthroughs."


def build_news_digest_html(articles: list, recipient_name: str = "Sudheer") -> str:
    """Builds an executive dark charcoal & amber gold HTML email digest."""
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
        badge_color = "#059669" if "OpenAI" in source else ("#d97706" if "Anthropic" in source else "#dc2626")

        card = f"""
        <div style="background-color: #232630; border: 1px solid #333845; border-radius: 12px; padding: 22px; margin-bottom: 22px;">
            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 12px;">
                <tr>
                    <td>
                        <span style="background-color: #2e3342; color: #f3f4f6; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; margin-right: 8px;">#{idx}</span>
                        <span style="background-color: {badge_color}; color: #ffffff; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; padding: 3px 10px; border-radius: 20px;">
                            {source}
                        </span>
                    </td>
                    <td align="right" style="color: #9ca3af; font-size: 12px; font-weight: 500;">
                        {pub_str}
                    </td>
                </tr>
            </table>
            <h2 style="margin: 0 0 10px 0; font-size: 18px; font-weight: 700; line-height: 1.35; color: #ffffff; letter-spacing: -0.2px;">
                <a href="{url}" style="color: #ffffff; text-decoration: none;" target="_blank">
                    {title}
                </a>
            </h2>
            <p style="margin: 0 0 14px 0; color: #d1d5db; font-size: 14px; line-height: 1.65;">
                {desc}
            </p>
            <a href="{url}" style="display: inline-block; background-color: #f59e0b; color: #111318; font-size: 12px; font-weight: 700; text-decoration: none; padding: 9px 18px; border-radius: 8px; letter-spacing: 0.2px;" target="_blank">
                Read full update &rarr;
            </a>
        </div>
        """
        cards_html.append(card)

    articles_section = "\n".join(cards_html)
    total_articles = len(articles)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily AI News Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: #121316; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; color: #f3f4f6;">
    <div style="background-color: #121316; padding: 36px 12px;">
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 620px; margin: 0 auto; background-color: #1a1c22; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6); border: 1px solid #2e323d;">
            <!-- Header Banner in Charcoal & Gold -->
            <tr>
                <td style="background: linear-gradient(135deg, #14161c 0%, #1f232d 50%, #262118 100%); padding: 36px 32px 30px 32px; border-bottom: 2px solid #f59e0b;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                            <td>
                                <div style="display: inline-block; background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; padding: 4px 12px; border-radius: 20px; margin-bottom: 14px;">
                                    ⚡ AI INTELLIGENCE DIGEST
                                </div>
                                <div style="color: #9ca3af; font-size: 12px; font-weight: 500; margin-bottom: 8px;">
                                    {date_str} &bull; Executive Briefing
                                </div>
                                <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 800; line-height: 1.3; color: #ffffff; letter-spacing: -0.4px;">
                                    Hello {recipient_name}, here is your latest AI News Update
                                </h1>
                                <p style="margin: 0; color: #d1d5db; font-size: 14px; line-height: 1.65; max-width: 520px;">
                                    We aggregated the most significant breakthroughs, research, and releases from top AI labs and creators.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- Section Label -->
            <tr>
                <td style="padding: 24px 32px 10px 32px; background-color: #1a1c22;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                            <td style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; color: #fbbf24;">
                                Featured Stories
                            </td>
                            <td align="right" style="font-size: 12px; color: #9ca3af; font-weight: 500;">
                                {total_articles} Curated Updates
                            </td>
                        </tr>
                    </table>
                    <div style="height: 1px; background-color: #2e323d; margin-top: 10px;"></div>
                </td>
            </tr>

            <!-- Articles List -->
            <tr>
                <td style="padding: 12px 32px 28px 32px; background-color: #1a1c22;">
                    {articles_section}
                </td>
            </tr>

            <!-- Footer -->
            <tr>
                <td style="padding: 24px 32px; background-color: #14161c; border-top: 1px solid #2e323d; text-align: center;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 600; color: #d1d5db;">
                        AI News Aggregator &bull; Intelligent News Pipeline
                    </p>
                    <p style="margin: 0; font-size: 11px; color: #9ca3af; line-height: 1.5;">
                        Delivered to {os.getenv('RECIPIENT_EMAIL') or os.getenv('MY_EMAIL', 'Configured Email')}.<br>
                        Powered by Google Gemini 2.5 Flash &amp; Automated Scrapers.
                    </p>
                </td>
            </tr>
        </table>
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
                "description": get_clean_article_summary(a.title, a.url, a.description, "OpenAI"),
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
                "description": get_clean_article_summary(a.title, a.url, a.description, "Anthropic"),
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
                    "description": get_clean_article_summary(v.title, v.url, v.description, "YouTube"),
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
