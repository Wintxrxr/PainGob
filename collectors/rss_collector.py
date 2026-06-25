import feedparser

from bs4 import BeautifulSoup

from collectors.base_collector import BaseCollector


class RSSCollector(BaseCollector):

    def collect_posts(
        self,
        feed_url: str,
        limit: int = 10,
    ) -> list[dict]:

        feed = feedparser.parse(feed_url)

        if feed.bozo:
            raise ValueError(
                f"Failed to parse RSS feed: {feed.bozo_exception}"
            )

        posts = []

        for entry in feed.entries[:limit]:

            html = (
                entry.get("summary")
                or entry.get("description")
                or ""
            )

            content = BeautifulSoup(
                html,
                "html.parser"
            ).get_text(" ", strip=True)

            post = self.normalize_post(
                title=entry.get("title", ""),
                content=content,
                url=entry.get("link", ""),
                published=entry.get("published", ""),
                source="rss",
                feed_name=feed.feed.get("title", ""),
            )

            if self.is_valid_post(post):
                posts.append(post)

        return posts