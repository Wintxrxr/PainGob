from collectors.collector_runner import run_collectors

def main() -> None:
    stats = run_collectors()
    total_posts = stats["posts_collected"]
    total_inserted = stats["posts_inserted"]  # all saved posts are considered inserted
    duplicates_skipped = stats["duplicates_skipped"]
    errors = stats["errors"]

    print(f"Posts collected: {total_posts}")
    print(f"Posts inserted: {total_inserted}")
    print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()