import sys
from sqlalchemy import text, inspect
from app.database.connection import get_database_info, engine

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check():
    db_info = get_database_info()

    print("\n" + "=" * 60)
    print("Database Connection Check")
    print("=" * 60)
    print(f"Environment: {db_info['environment']}")
    print(f"Database URL: {db_info['url_masked']}")
    print(f"Host: {db_info['host']}")
    print("=" * 60 + "\n")

    try:
        with engine.connect() as conn:
            if db_info.get("is_sqlite"):
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                print("[OK] Connection successful!")
                print(f"[OK] SQLite version: {version}")
            else:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print("[OK] Connection successful!")
                print(f"[OK] PostgreSQL version: {version.split(',')[0]}")

            inspector = inspect(engine)
            tables = inspector.get_table_names()

            if "digests" in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM digests"))
                count = result.scalar()
                print(f"[OK] Digests table exists with {count} records")

                columns = [c["name"] for c in inspector.get_columns("digests")]
                if "sent_at" in columns:
                    print("[OK] sent_at column exists")
                else:
                    print("[WARN] sent_at column does not exist (run migration)")
            else:
                print("[INFO] Tables do not exist yet. Run `uv run python -m app.database.create_tables` to initialize.")

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check()
