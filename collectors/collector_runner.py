import feedparser

from collectors.base_collector import BaseCollector


class RSSCollector(BaseCollector):
   
    def collect_posts(self, feed_url: str, limit: int = 10) -> list[dict]:
        feed = feedparser.parse(feed_url)

        if feed.bozo:
            raise ValueError(
                f"Failed to parse RSS feed: {feed.bozo_exception}"
            )

        posts = []

        for entry in feed.entries[:limit]:

            content = (
                entry.get("summary")
                or entry.get("description")
                or ""
            )

            post = {
                "title": entry.get("title", ""),
                "content": content,
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": "RSS",
                "feed_name": feed.feed.get("title", ""),
            }

            posts.append(post)

        return posts