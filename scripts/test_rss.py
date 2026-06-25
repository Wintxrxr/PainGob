from collectors.rss_collector import RSSCollector


collector = RSSCollector()

posts = collector.collect_posts(
    feed_url="https://hnrss.org/frontpage",
    limit=5,
)

for i, post in enumerate(posts, start=1):
    print("=" * 80)
    print(f"Post {i}")
    print(f"Title      : {post['title']}")
    print(f"Source     : {post['source']}")
    print(f"Feed       : {post['feed_name']}")
    print(f"Published  : {post['published']}")
    print(f"URL        : {post['url']}")