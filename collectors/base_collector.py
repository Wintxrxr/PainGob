from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
  

    @abstractmethod
    def collect_posts(self) -> list[dict[str, Any]]:
       
        raise NotImplementedError

    def normalize_post(
        self,
        *,
        title: str,
        content: str,
        url: str,
        source: str,
        published: str = "",
        feed_name: str = "",
        author: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
   

        return {
            "title": self.clean_text(title),
            "content": self.clean_text(content),
            "url": self.clean_text(url),
            "source": source.lower(),
            "published": published,
            "feed_name": feed_name,
            "author": author,
            "metadata": metadata or {},
        }

    @staticmethod
    def clean_text(text: str | None) -> str:
    

        if not text:
            return ""

        return " ".join(text.split())

    @staticmethod
    def is_valid_post(post: dict[str, Any]) -> bool:
      

        required_fields = (
            "title",
            "content",
            "url",
            "source",
        )

        return all(post.get(field) for field in required_fields)