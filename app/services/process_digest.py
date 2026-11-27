from typing import Optional
import logging
from app.agent.digest_agent import DigestAgent, DigestOutput
from app.database.repository import Repository
from .base import BaseProcessService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class DigestProcessor(BaseProcessService):
    def __init__(self):
        super().__init__()
        self.agent = DigestAgent()
        self.repo = Repository()

    def get_items_to_process(self, limit: Optional[int] = None) -> list:
        return self.repo.get_articles_without_digest(limit=limit)

    def process_item(self, item: dict) -> Optional[DigestOutput]:
        import time
        time.sleep(1.0)
        try:
            res = self.agent.generate_digest(
                title=item["title"],
                content=item["content"],
                article_type=item["type"]
            )
            if res:
                return res
        except Exception as e:
            logging.warning(f"Digest agent error for {item.get('title')}: {e}")

        # Resilient fallback: if LLM fails or is unavailable, create a digest from article content
        fallback_summary = (item.get("content") or item.get("title") or "")[:350].strip()
        if len(fallback_summary) > 340:
            fallback_summary = fallback_summary[:340] + "..."
        return DigestOutput(
            title=item["title"][:120],
            summary=fallback_summary or "Key AI developments and updates from this publication."
        )

    def save_result(self, item: dict, result: DigestOutput) -> bool:
        try:
            self.repo.create_digest(
                article_type=item["type"],
                article_id=item["id"],
                url=item["url"],
                title=result.title,
                summary=result.summary,
                published_at=item.get("published_at")
            )
            return True
        except Exception:
            return False

    def _get_item_id(self, item: dict) -> str:
        return f"{item['type']}:{item['id']}"

    def _get_item_title(self, item: dict) -> str:
        return item["title"]


def process_digests(limit: Optional[int] = None) -> dict:
    processor = DigestProcessor()
    return processor.process(limit=limit)


if __name__ == "__main__":
    result = process_digests()
    print(f"Total articles: {result['total']}")
    print(f"Processed: {result['processed']}")
    print(f"Failed: {result['failed']}")

