import os
import sys
import argparse
import requests
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def show_local_subscribers():
    from app.database.connection import engine
    from app.database.models import Subscriber
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        subscribers = session.query(Subscriber).order_by(Subscriber.id.asc()).all()
        print("\n" + "=" * 95)
        print(" [LOCAL DATABASE] Subscribers Table")
        print("=" * 95)
        if not subscribers:
            print(" [!] No subscribers found in your local database.")
            print("     (Tip: Run 'python scripts/view_subscribers.py --cloud' to view live Render subscribers)")
            print("=" * 95 + "\n")
            return

        print(f"{'ID':<4} | {'Name':<18} | {'Email':<30} | {'Priority 1':<12} | {'Priority 2':<12} | {'Active'}")
        print("-" * 95)
        for s in subscribers:
            status = "YES" if s.is_active else "NO"
            print(f"{s.id:<4} | {s.name:<18} | {s.email:<30} | {s.priority_1:<12} | {s.priority_2:<12} | {status}")
        print("=" * 95)
        print(f"Total Local Subscribers: {len(subscribers)}\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to query local database: {e}\n")
    finally:
        session.close()


def show_cloud_subscribers():
    url = "https://news2u.onrender.com/api/subscribers"
    print("\n" + "=" * 95)
    print(" [LIVE CLOUD RENDER] Subscribers Table (https://news2u.onrender.com)")
    print("=" * 95)
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            subscribers = data.get("subscribers", [])
            if not subscribers:
                print(" [!] No active subscribers found on Render.")
                print("=" * 95 + "\n")
                return

            print(f"{'#':<4} | {'Name':<18} | {'Email (Masked)':<30} | {'Priority 1':<12} | {'Priority 2':<12} | {'Registered At'}")
            print("-" * 95)
            for idx, s in enumerate(subscribers, 1):
                created = (s.get("created_at") or "")[:19].replace("T", " ")
                print(f"{idx:<4} | {s.get('name', ''):<18} | {s.get('email', ''):<30} | {s.get('priority_1', ''):<12} | {s.get('priority_2', ''):<12} | {created}")
            print("=" * 95)
            print(f"Total Active Cloud Subscribers: {data.get('total_active', len(subscribers))}\n")
        else:
            print(f"[!] Server returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[ERROR] Failed to reach Render API: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View NEWS2U Subscribers Table")
    parser.add_argument("--cloud", action="store_true", help="View live cloud subscribers from Render")
    args = parser.parse_args()

    if args.cloud:
        show_cloud_subscribers()
    else:
        show_local_subscribers()
        show_cloud_subscribers()
