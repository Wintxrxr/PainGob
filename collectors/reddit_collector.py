import praw

from config.settings import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT
)


class RedditCollector:

    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )

    def collect_posts(
        self,
        subreddit_name: str,
        limit: int = 10
    ):
        posts = []

        subreddit = self.reddit.subreddit(subreddit_name)

        for post in subreddit.hot(limit=limit):

            posts.append(
                {
                    "title": post.title,
                    "content": post.selftext,
                    "score": post.score,
                    "url": post.url,
                    "subreddit": subreddit_name,
                }
            )

        return posts