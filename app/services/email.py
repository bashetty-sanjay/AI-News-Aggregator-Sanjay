import os
import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import markdown

load_dotenv()

MY_EMAIL = os.getenv("MY_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL") or MY_EMAIL
APP_PASSWORD = os.getenv("APP_PASSWORD")


def send_email(subject: str, body_text: str, body_html: str = None, recipients: list = None):
    sender_email = (os.getenv("MY_EMAIL") or MY_EMAIL or "").strip()
    raw_app_password = os.getenv("APP_PASSWORD") or APP_PASSWORD or ""
    app_password = raw_app_password.replace(" ", "").strip()
    default_recipient = (os.getenv("RECIPIENT_EMAIL") or sender_email).strip()

    if recipients is None:
        recipients = [default_recipient]

    recipients = [r for r in recipients if r is not None and r.strip()]
    if not recipients:
        raise ValueError("No valid recipient email provided. Please set RECIPIENT_EMAIL or MY_EMAIL in .env")

    if not sender_email:
        raise ValueError("MY_EMAIL environment variable is not set")
    if not app_password:
        raise ValueError(
            "APP_PASSWORD environment variable is not set. "
            "To send emails via Gmail SMTP, please generate a 16-character Google App Password "
            "from https://myaccount.google.com/apppasswords and set APP_PASSWORD in your .env file."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)

    part1 = MIMEText(body_text, "plain")
    msg.attach(part1)

    if body_html:
        part2 = MIMEText(body_html, "html")
        msg.attach(part2)

    sent = False
    last_err = None

    # Strategy 1: Try Port 587 with STARTTLS (recommended for cloud hosts like Render)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(sender_email, app_password)
            smtp.sendmail(sender_email, recipients, msg.as_string())
            sent = True
    except Exception as e:
        last_err = e

    # Strategy 2: Fallback to Port 465 with SSL
    if not sent:
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
                smtp.login(sender_email, app_password)
                smtp.sendmail(sender_email, recipients, msg.as_string())
                sent = True
        except Exception as e:
            last_err = e

    if not sent:
        raise RuntimeError(f"Could not deliver email via Gmail SMTP (ports 587 & 465 failed): {last_err}")


def markdown_to_html(markdown_text: str) -> str:
    html = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""


def digest_to_html(digest_response) -> str:
    from datetime import datetime
    from app.agent.email_agent import EmailDigestResponse

    if not isinstance(digest_response, EmailDigestResponse):
        return markdown_to_html(digest_response.to_markdown() if hasattr(digest_response, 'to_markdown') else str(digest_response))

    date_str = datetime.now().strftime("%B %d, %Y")
    greeting_raw = digest_response.introduction.greeting.strip()
    intro_raw = digest_response.introduction.introduction.strip()

    cards_html = []
    for article in digest_response.articles:
        raw_source = getattr(article, "article_type", "AI").lower()
        if "openai" in raw_source:
            source_label = "OpenAI"
            badge_bg = "#059669"
            action_text = "Read on OpenAI"
        elif "anthropic" in raw_source:
            source_label = "Anthropic"
            badge_bg = "#d97706"
            action_text = "Read on Anthropic"
        elif "youtube" in raw_source:
            source_label = "YouTube"
            badge_bg = "#dc2626"
            action_text = "Watch on YouTube"
        else:
            source_label = raw_source.capitalize()
            badge_bg = "#4f46e5"
            action_text = "Read full article"

        rank = getattr(article, "rank", None)
        rank_badge = f'<span style="background-color: #0a192f; color: #93c5fd; border: 1px solid #1e3a5f; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; margin-right: 8px;">#{rank}</span>' if rank else ""

        # Format summary markdown to html
        summary_html = markdown.markdown(article.summary, extensions=['extra', 'nl2br'])

        reasoning_html = ""
        if getattr(article, "reasoning", None):
            reasoning_html = f"""
            <div style="background-color: #181a20; border-left: 3px solid #f59e0b; border-radius: 6px; padding: 12px 14px; margin-bottom: 16px;">
                <strong style="color: #fbbf24; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;">Why this matters:</strong>
                <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 13px; line-height: 1.5;">
                    {html.escape(article.reasoning)}
                </p>
            </div>
            """

        card = f"""
        <div style="background-color: #232630; border: 1px solid #333845; border-radius: 12px; padding: 22px; margin-bottom: 22px;">
            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 12px;">
                <tr>
                    <td>
                        <span style="background-color: #2e3342; color: #f3f4f6; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; margin-right: 8px;">#{rank or 1}</span>
                        <span style="background-color: {badge_bg}; color: #ffffff; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; padding: 3px 10px; border-radius: 20px;">
                            {source_label}
                        </span>
                    </td>
                </tr>
            </table>
            <h2 style="margin: 0 0 10px 0; font-size: 18px; font-weight: 700; line-height: 1.35; color: #ffffff; letter-spacing: -0.2px;">
                <a href="{html.escape(article.url)}" style="color: #ffffff; text-decoration: none;" target="_blank">
                    {html.escape(article.title)}
                </a>
            </h2>
            <div style="color: #d1d5db; font-size: 14px; line-height: 1.65; margin-bottom: 14px;">
                {summary_html}
            </div>
            {reasoning_html}
            <a href="{html.escape(article.url)}" style="display: inline-block; background-color: #f59e0b; color: #111318; font-size: 12px; font-weight: 700; text-decoration: none; padding: 9px 18px; border-radius: 8px; letter-spacing: 0.2px;" target="_blank">
                {action_text} &rarr;
            </a>
        </div>
        """
        cards_html.append(card)

    articles_section = "\n".join(cards_html)
    recipient_email = os.getenv("RECIPIENT_EMAIL") or os.getenv("MY_EMAIL", "")
    total_articles = len(digest_response.articles)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEWS2U - Daily AI Digest</title>
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
                                    ⚡ NEWS2U &bull; AI INTELLIGENCE DIGEST
                                </div>
                                <div style="color: #9ca3af; font-size: 12px; font-weight: 500; margin-bottom: 8px;">
                                    {date_str} &bull; Executive Briefing
                                </div>
                                <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 800; line-height: 1.3; color: #ffffff; letter-spacing: -0.4px;">
                                    {html.escape(greeting_raw)}
                                </h1>
                                <p style="margin: 0; color: #d1d5db; font-size: 14px; line-height: 1.65; max-width: 520px;">
                                    {html.escape(intro_raw)}
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
                        Delivered to {html.escape(recipient_email)}.<br>
                        <strong>NEWS2U</strong> &bull; Powered by Google Gemini 2.5 Flash &amp; Automated Scrapers.<br>
                        <a href="https://news2u.onrender.com/unsubscribe?email={html.escape(recipient_email)}" style="color: #6b7280; text-decoration: underline; font-size: 11px; display: inline-block; margin-top: 8px;">Unsubscribe from daily briefings</a>
                    </p>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>"""


def send_email_to_self(subject: str, body: str, body_html: str = None):
    target = os.getenv("RECIPIENT_EMAIL") or os.getenv("MY_EMAIL")
    if not target:
        raise ValueError("Neither RECIPIENT_EMAIL nor MY_EMAIL is set in .env")
    send_email(subject, body, body_html=body_html, recipients=[target])


if __name__ == "__main__":
    import sys
    target = os.getenv("RECIPIENT_EMAIL") or os.getenv("MY_EMAIL")
    print(f"Testing email sending to {target}...")
    try:
        send_email_to_self(
            "Test from AI News Aggregator",
            "This is a test notification from your AI News Aggregator system.",
            "<h3>AI News Aggregator Test</h3><p>Your email configuration is working successfully!</p>"
        )
        print("[OK] Test email sent successfully!")
    except Exception as e:
        print(f"[ERROR] Could not send test email: {e}")
        sys.exit(1)