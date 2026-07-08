"""
Collector runner – orchestrates RSS / Reddit collection,
normalises posts and persists them via PostService.
"""

import logging
import time
from typing import Dict, List

from config.settings import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
)

from collectors.rss_collector import RSSCollector
from collectors.reddit_collector import RedditCollector
from services.post_service import PostService
from database.session import get_db
from sqlalchemy.orm import session_scope

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration – extend / move to settings as needed
# ---------------------------------------------------------------------------
RSS_FEED_URLS: List[str] = [
    "https://example.com/feed.xml",   # placeholder – replace with real feeds
]

REDDIT_SUBREDDITS: List[str] = [
    "programming", "python", "MachineLearning"
]

# ---------------------------------------------------------------------------
# 
# 
def run_collectors() -> Dict[str, int]:
    """
    Execute all registered collectors, normalise their output,
    persist via PostService and return statistics.
    """
    stats = {
        "posts_collected": 0,
        "posts_inserted": 0,
        "duplicates_skipped": 0,
        "errors": 0,
    }

    # one DB session for the whole run
    with session_scope() as db:
        post_service = PostService(db)

    # -----------------------------------------------------------------------
    # Collectors – each entry is a tuple (collector_instance, kwargs_iterable)
    # -----------------------------------------------------------------------
    collector_jobs = [
        (RSSCollector(), ({"feed_url": url, "limit": 20} for url in RSS_FEED_URLS)),
        (RedditCollector(), ({"subreddit_name": sub, "limit": 20} for sub in REDDIT_SUBREDDITS)),
    ]

    for collector, kwarg_iter in collector_jobs:
        collector_name = collector.__class__.__name__
        start = time.perf_counter()
        for kwargs in kwarg_iter:
            try:
                raw_posts = collector.collect_posts(**kwargs)
            except Exception as exc:                     # pragma: no cover
                log.exception("Collector %s failed: %s", collector_name, exc)
                stats["errors"] += 1
                continue

            stats["posts_collected"] += len(raw_posts)

            for post_dict in raw_posts:
                try:
                    post_service.create_post(post_dict)   # assumes PostService.create_post
                    stats["posts_inserted"] += 1
                except Exception as exc:                  # pragma: no cover
                    # Duplicate key (url+source) or any other DB error → count & continue
                    if "duplicate key" in str(exc).lower():
                        stats["duplicates_skipped"] += 1
                    else:
                        log.exception("Failed to persist post: %s", exc)
                        stats["errors"] += 1

        elapsed = time.perf_counter() - start
        log.info("%s finished in %.2fs – collected %d posts", collector_name, elapsed, stats["posts_collected"])

    return stats

if __name__ == "__main__":          # manual test
    logging.basicConfig(level=logging.INFO)
    result = run_collectors()
    print(result)