"""
PostService – thin persistence layer for ``Post`` entities.

All public methods run inside a session factory so that each logical operation gets
its own transaction with automatic commit / rollback.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Callable
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import Post
from database.session import session_scope

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Result:
    inserted: int = 0
    duplicates: int = 0
    failed: int = 0


def _parse_published(value: Optional[str]) -> Optional[datetime]:
    """Parse a published string into a timezone‑aware ``datetime``."""
    if not value:
        return None
    # ``dateutil`` is a dependency of the project; fall back to ``fromisoformat``.
    try:
        from dateutil import parser as date_parser
        dt = date_parser.isoparse(value)
    except Exception:
        dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return dt


def _validate_required(post_data: dict) -> None:
    missing = [field for field in ("title", "url", "source") if not post_data.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


class _SessionContext:
    """Wrap a plain Session to look like a context manager without closing it."""
    def __init__(self, session: Session):
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        else:
            self._session.commit()


class PostService:
    """Persistence helpers for ``Post`` ORM objects."""

    def __init__(self, session_factory):
        """
        ``session_factory`` can be either:
        * a callable returning a context‑managed ``Session`` (e.g. ``session_scope``), or
        * an already‑opened ``Session`` instance (the caller manages its lifecycle).

        The default uses the project‑wide ``session_scope`` helper.
        """
        if callable(session_factory):
            self._session_factory = session_factory
        else:
            # Assume a Session instance was passed.
            self._session_factory = lambda: _SessionContext(session_factory)

    # ------------------------------------------------------------------ create
    def create_post(self, post_data: dict) -> Result:
        """Persist a single post, returning a ``Result``."""
        _validate_required(post_data)
        log.info("Creating post: %s", post_data.get("url"))
        result = Result()
        try:
            with self._session_factory() as db:
                stmt = (
                    pg_insert(Post)
                    .values(
                        title=post_data.get("title", ""),
                        content=post_data.get("content", ""),
                        url=post_data.get("url", ""),
                        source=post_data.get("source", "").lower(),
                        published_at=_parse_published(post_data.get("published")),
                        feed_name=post_data.get("feed_name", ""),
                        author=post_data.get("author", ""),
                        raw_metadata=post_data.get("metadata", {}),
                        status=post_data.get("status", "NEW"),
                    )
                    .on_conflict_do_nothing(
                        index_elements=["url", "source"]
                    )
                    .returning(Post.id)
                )
                inserted = db.execute(stmt).scalar_one_or_none()
                if inserted:
                    result.inserted = 1
                    log.debug("Post inserted successfully")
                else:
                    result.duplicates = 1
                    log.warning("Duplicate post (url+source): %s", post_data.get("url"))
        except IntegrityError as exc:
            log.warning("Integrity error while inserting post: %s", exc)
            result.duplicates = 1
        except Exception as exc:  # pragma: no cover
            log.exception("Failed to create post: %s", exc)
            raise RuntimeError(f"Post creation failed: {exc}") from exc
        return result

    def bulk_create(self, posts: List[dict]) -> Result:
        """Persist many posts efficiently using PostgreSQL ``ON CONFLICT DO NOTHING``."""
        log.info("Bulk creating %d posts", len(posts))
        result = Result()
        if not posts:
            return result

        # Validate all rows first
        for p in posts:
            _validate_required(p)

        try:
            with self._session_factory() as db:
                values = [
                    {
                        "title": p.get("title", ""),
                        "content": p.get("content", ""),
                        "url": p.get("url", ""),
                        "source": p.get("source", "").lower(),
                        "published_at": _parse_published(p.get("published")),
                        "feed_name": p.get("feed_name", ""),
                        "author": p.get("author", ""),
                        "raw_metadata": p.get("metadata", {}),
                        "status": p.get("status", "NEW"),
                    }
                    for p in posts
                ]

                stmt = (
                    pg_insert(Post)
                    .values(values)
                    .on_conflict_do_nothing(index_elements=["url", "source"])
                    .returning(Post.id)
                )
                inserted_ids = db.execute(stmt).scalars().all()
                result.inserted = len(inserted_ids)
                result.duplicates = len(posts) - result.inserted
                log.debug("Bulk insert completed: %d inserted, %d duplicates", result.inserted, result.duplicates)
        except Exception as exc:  # pragma: no cover
            log.exception("Bulk insert failed with unexpected error: %s", exc)
            raise RuntimeError(f"Bulk post creation failed: {exc}") from exc
        return result

    # ------------------------------------------------------------------ read
    def get_post(self, post_id: UUID) -> Optional[Post]:
        """Return a ``Post`` by primary key or ``None`` if not found."""
        with self._session_factory() as db:
            return db.get(Post, post_id)

    def get_recent_posts(self, limit: int = 100) -> List[Post]:
        """Return the most recent posts ordered by ``created_at`` descending."""
        with self._session_factory() as db:
            stmt = select(Post).order_by(Post.created_at.desc()).limit(limit)
            return db.execute(stmt).scalars().all()

    def post_exists(self, url: str, source: str) -> bool:
        """Fast existence check using the unique constraint columns."""
        with self._session_factory() as db:
            stmt = select(Post.id).where(Post.url == url, Post.source == source.lower())
            return db.execute(stmt).first() is not None

    # ------------------------------------------------------------------ status helpers
    def update_status(self, post_id: UUID, status: str) -> bool:
        """Set ``status`` on a post. Returns ``True`` if a row was updated."""
        with self._session_factory() as db:
            stmt = (
                update(Post)
                .where(Post.id == post_id)
                .values(status=status)
                .execution_options(synchronize_session="fetch")
            )
            result = db.execute(stmt)
            return result.rowcount > 0

    def mark_analyzed(self, post_id: UUID) -> bool:
        """Mark a post as ``ANALYZED``."""
        return self.update_status(post_id, "ANALYZED")

    def mark_failed(self, post_id: UUID, error_message: str = "") -> bool:
        """Mark a post as ``FAILED`` and optionally store an error message in ``raw_metadata``."""
        with self._session_factory() as db:
            stmt = (
                update(Post)
                .where(Post.id == post_id)
                .values(status="FAILED", raw_metadata={"error": error_message})
                .execution_options(synchronize_session="fetch")
            )
            result = db.execute(stmt)
            return result.rowcount > 0