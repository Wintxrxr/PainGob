from collectors.reddit_collector import RedditCollector

collector = RedditCollector()

posts = collector.collect_posts(
    subreddit_name="startups",
    limit=5
)

for post in posts:
    print("-" * 50)
    print(post["title"])
    print(post["score"])
    print(post["url"])