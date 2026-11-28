import sys
import subprocess

def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "send"
    
    if arg in ("web", "dev", "start"):
        print("\n🚀 Starting NEWS2U Web Server at http://localhost:8000 ...\n")
        subprocess.run([sys.executable, "-m", "uvicorn", "app.web:app", "--reload", "--port", "8000"])
    elif arg in ("subscribers", "users", "table"):
        print("\n📋 Loading Subscribers Table ...\n")
        subprocess.run([sys.executable, "scripts/view_subscribers.py"])
    else:
        print("\n🤖 Running NEWS2U Pipeline (Scrape -> Rank -> Digest -> Send Email) ...\n")
        subprocess.run([sys.executable, "-m", "app.daily_runner"])

if __name__ == "__main__":
    main()
