from collectors.collector_runner import run_collectors

def main() -> None:
    stats = run_collectors()
    total_posts = stats["posts_saved"]
    total_inserted = total_posts  # all saved posts are considered inserted
    duplicates_skipped = 0
    errors = stats["failed_collectors"]

    print(f"Posts collected: {total_posts}")
    print(f"Posts inserted: {total_inserted}")
    print(f"Duplicates skipped: {duplicates_skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()