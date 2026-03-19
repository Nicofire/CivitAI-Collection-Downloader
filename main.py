"""Main script for CivitAI Collection Downloader."""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
# import yaml

from config import init_config, config, setup_logging
from api import CivitaiAPI, extract_metadata, create_collection_metadata
from downloader import create_download_directory, download_media, save_metadata, sanitize_filename

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download images, videos, and metadata from CivitAI posts, image collections, or post collections."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--collection", type=str, nargs='+', help="Collection ID(s) to download. Can specify multiple IDs.")
    group.add_argument("-p", "--post", type=str, nargs='+', help="Post ID(s) to download. Can specify multiple IDs.")
    group.add_argument("-cp", "--collection-posts", type=str, nargs='+', help="Collection ID(s) where all unique posts should be downloaded.")

    parser.add_argument("-o", "--output", type=str, help="Override default download location")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--no-metadata", action="store_true", help="Skip metadata generation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")

    return parser.parse_args()

def process_collection(api, collection_id, dry_run=False, skip_metadata=False, api_key=None):
    """Process a collection and download its media and metadata."""
    try:
        download_dir = create_download_directory(collection_id)

        media_items = api.get_all_images_in_collection(collection_id)
        if not media_items:
            logging.error("No media found in collection: %s", collection_id)
            return False

        logging.info("Found %d media items in collection: %s", len(media_items), collection_id)

        downloaded_items = []
        items_metadata = []

        for i, item in enumerate(media_items):
            item_id = item.get("id")
            logging.info("Processing item %d/%d: ID %s", i+1, len(media_items), item_id)

            item_details = api.get_image_details(item_id) or item

            metadata = extract_metadata(api, item_details)
            items_metadata.append(metadata)

            if not dry_run:
                downloaded_file = download_media(item_details, download_dir, api_key)
                if downloaded_file:
                    downloaded_items.append(downloaded_file)
                    if not skip_metadata:
                        base_name = downloaded_file.stem
                        meta_path = download_dir / f"{base_name}_metadata.json"
                        save_metadata(metadata, meta_path)

        if not skip_metadata and not dry_run and items_metadata:
            collection_data = api.get_collection_by_id(collection_id)

            if collection_data:
                collection_metadata = create_collection_metadata(api, collection_id, items_metadata)
            else:
                collection_metadata = {
                    "id": collection_id,
                    "name": f"Collection-{collection_id}",
                    "media_count": len(items_metadata),
                    "media": items_metadata
                }

            metadata_path = download_dir / "collection_metadata.json"
            save_metadata(collection_metadata, metadata_path)

        logging.info("Successfully processed %d of %d items from collection %s", len(downloaded_items) if not dry_run else len(items_metadata), len(media_items), collection_id)
        return True
    except Exception as e:
        logging.error("Error processing collection %s: %s", collection_id, e)
        return False

def process_post(api, post_id, dry_run=False, skip_metadata=False, api_key=None, base_output_dir=None):
    """Process a single post and download its media and metadata."""
    post = api.get_post_by_id(post_id)
    if not post:
        logging.error("Failed to get post with ID: %s", post_id)
        return False

    download_dir_base = base_output_dir if base_output_dir is not None else config.get('download_dir')
    if not download_dir_base:
        download_dir_base = os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI')
        logging.warning("Download directory not found in config, using default: %s", download_dir_base)

    post_title = post.get("title", "") if post else ""
    if post_title:
        download_dir = Path(download_dir_base) / f"{post_id}-{sanitize_filename(post_title)}"
    else:
        download_dir = Path(download_dir_base) / f"{post_id}"
    download_dir.mkdir(parents=True, exist_ok=True)

    media_items = api.get_all_images_in_post(post_id)
    if not media_items:
        logging.error("No media found in post: %s", post_id)
        return False

    logging.info("Found %d media items in post: %s", len(media_items), post_id)

    downloaded_items = []
    items_metadata = []

    for i, item in enumerate(media_items):
        item_id = item.get("id")
        logging.info("Processing item %d/%d: ID %s", i+1, len(media_items), item_id)

        item_details = api.get_image_details(item_id) or item

        metadata = extract_metadata(api, item_details)
        items_metadata.append(metadata)

        if not dry_run:
            downloaded_file = download_media(item_details, download_dir, api_key)
            if downloaded_file:
                downloaded_items.append(downloaded_file)
                if not skip_metadata:
                    base_name = downloaded_file.stem
                    meta_path = download_dir / f"{base_name}_metadata.json"
                    save_metadata(metadata, meta_path)

    if not skip_metadata and not dry_run:
        post_metadata = {
            "id": post_id,
            "title": post_title,
            "media_count": len(items_metadata),
            "media": items_metadata
        }
        metadata_path = download_dir / "post_metadata.json"
        save_metadata(post_metadata, metadata_path)

    logging.info("Successfully downloaded %d of %d items from post %s", len(downloaded_items), len(media_items), post_id)
    return True

def process_collection_posts(api, collection_id, dry_run=False, skip_metadata=False, api_key=None):
    """Download all unique posts referenced by media in a collection."""
    try:
        collection_data = api.get_collection_by_id(collection_id)
        if collection_data:
            collection_dir = create_download_directory(collection_data)
            collection_name = collection_data.get("collection", {}).get("name", "Collection-%s" % collection_id)
        else:
            collection_dir = create_download_directory(collection_id)
            collection_name = "Collection-%s" % collection_id

        posts = api.get_all_posts_in_collection(collection_id)
        if not posts:
            logging.error("No posts found in collection: %s", collection_id)
            return False

        post_ids = []
        seen_post_ids = set()

        for item in posts:
            post_id = item.get("id")
            if post_id is not None and post_id not in seen_post_ids:
                seen_post_ids.add(post_id)
                post_ids.append(post_id)

        if not post_ids:
            logging.error("No posts found in collection: %s", collection_id)
            return False

        logging.info("Found %d unique posts in collection %s", len(post_ids), collection_id)

        successful_posts = 0
        for idx, post_id in enumerate(post_ids, start=1):
            logging.info("Processing post %d/%d from collection %s: %s", idx, len(post_ids), collection_id, post_id)
            post_success = process_post(
                api,
                str(post_id),
                dry_run=dry_run,
                skip_metadata=skip_metadata,
                api_key=api_key,
                base_output_dir=collection_dir
            )
            if post_success:
                successful_posts += 1

        if not skip_metadata and not dry_run:
            collection_posts_metadata = {
                "id": collection_id,
                "name": collection_name,
                "post_count": len(post_ids),
                "successful_posts": successful_posts,
                "posts": [str(pid) for pid in post_ids]
            }
            metadata_path = Path(collection_dir) / "collection_posts_metadata.json"
            save_metadata(collection_posts_metadata, metadata_path)

        logging.info(
            "Successfully processed %d of %d posts from collection %s", successful_posts, len(post_ids), collection_id
        )
        return successful_posts == len(post_ids)

    except Exception as e:
        logging.error("Error processing collection posts %s: %s", collection_id, e)
        return False

def main():
    """Main function to run the CivitAI downloader."""
    # Parse command line arguments
    args = parse_arguments()

    # Initialize configuration
    init_config()

    # Override download directory if specified
    if args.output:
        config['download_dir'] = args.output

    # Setup logging
    if args.verbose:
        config['log_level'] = 'DEBUG'
    logger = setup_logging()

    logger.info("Starting CivitAI Downloader")

    # Get API key and verify it exists
    api_key = config.get('api_key')
    if not api_key:
        logger.error("No API key found in configuration")
        return 1

    logger.debug("Using API key: %s***%s", api_key[:4], api_key[-4:] if len(api_key) > 8 else '')
    api = CivitaiAPI(api_key)

    start_time = time.time()
    success = True  # Changed to track overall success

    try:
        if args.collection:
            for collection_id in args.collection:
                logger.info("Processing collection: %s", collection_id)
                collection_success = process_collection(api, collection_id, args.dry_run, args.no_metadata, api_key)
                success = success and collection_success  # Only stays True if all succeed

        elif args.collection_posts:
            for collection_id in args.collection_posts:
                logger.info("Processing collection as posts: %s", collection_id)
                collection_success = process_collection_posts(api, collection_id, args.dry_run, args.no_metadata, api_key)
                success = success and collection_success  # Only stays True if all succeed

        elif args.post:
            for post_id in args.post:
                logger.info("Processing post: %s", post_id)
                post_success = process_post(api, post_id, args.dry_run, args.no_metadata, api_key)
                success = success and post_success  # Only stays True if all succeed

    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        success = False

    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        success = False

    elapsed_time = time.time() - start_time
    logger.info("Download completed in %.2f seconds", elapsed_time)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
