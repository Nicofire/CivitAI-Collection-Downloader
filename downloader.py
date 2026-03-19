"""Module for downloading media files and saving metadata for CivitAI collections."""
import os
import sys
import json
import time
import logging
import mimetypes
from pathlib import Path
# from urllib.parse import urlparse
import requests

from config import config

logger = logging.getLogger(__name__)

# Initialize mimetypes
mimetypes.init()
# Ensure common MIME types are properly mapped
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('video/mp4', '.mp4')

def get_file_extension(mime_type):
    """Get the appropriate file extension for a MIME type."""
    # Special case handling for common types
    mime_to_ext = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'video/mp4': '.mp4',
        'video/quicktime': '.mov',
        'video/webm': '.webm'
    }

    if mime_type in mime_to_ext:
        return mime_to_ext[mime_type]

    # Fall back to system MIME type mapping
    ext = mimetypes.guess_extension(mime_type)
    return ext or ''

def sanitize_filename(filename):
    """Sanitize filename to be filesystem-safe."""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Replace spaces with underscores for consistency
    filename = filename.replace(' ', '_')

    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        base, ext = os.path.splitext(filename)
        filename = base[:200] + ext

    return filename

def create_download_directory(collection_info):
    """Create a directory for downloading files based on collection info."""
    # Ensure we have a valid download directory
    download_dir = config.get('download_dir')
    if not download_dir:
        download_dir = os.path.join(os.path.expanduser('~'), 'Pictures', 'CivitAI')
        logger.warning("Download directory not found in config, using default: %s", download_dir)

    base_dir = Path(download_dir)

    # Handle different types of input for collection_info
    if collection_info is None:
        # Use ID from command line args as fallback
        collection_id = "unknown-collection"
        if len(sys.argv) > 2 and sys.argv[1] in ['-c', '--collection']:
            collection_id = sys.argv[2]
        logger.warning("No collection info available, using ID: %s", collection_id)
        download_dir = base_dir / str(collection_id)
    elif isinstance(collection_info, dict) and "collection" in collection_info:
        # Full collection object from API
        collection_name = collection_info.get("collection", {}).get("name")
        collection_id = collection_info.get("collection", {}).get("id")

        # Create directory name based on collection ID and name
        if collection_name:
            dir_name = f"{collection_id}-{sanitize_filename(collection_name)}"
        else:
            dir_name = f"{collection_id}"

        download_dir = base_dir / dir_name
    else:
        # Assume collection_info is just the ID
        collection_id = collection_info
        download_dir = base_dir / str(collection_id)

    # Create the directory
    download_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Created download directory: %s", download_dir)
    return download_dir

def download_file(url, output_path, mime_type=None, max_retries=3, api_key=None):
    """Download a file from a URL to the specified path with retry logic."""
    # Ensure URL is complete with domain if it's just a path
    if not url.startswith('http'):
        # Use the provided API key
        if not api_key:
            logger.error("No API key provided for download")
            return False

        # Extract filename from the output path
        filename = os.path.basename(output_path)

        # Construct URL exactly like the original script
        original_url = url
        url = f"https://image.civitai.com/{api_key}/{url}/{filename}"
        logger.debug("Constructed download URL from '%s' to '%s'", original_url, url)

    logger.info("Downloading file to %s", output_path)
    logger.debug("Download URL: %s", url)

    for attempt in range(max_retries + 1):
        try:
            # Simple request without session, exactly like original script
            logger.debug("Download attempt %d/%d", attempt+1, max_retries+1)
            with requests.get(url, stream=True, timeout=30) as response:
                logger.debug("Response status: %s", response.status_code)
                logger.debug("Response headers: %s", dict(response.headers))
                response.raise_for_status()

                # Check if MIME type matches expected
                content_type = response.headers.get('Content-Type', '')
                if mime_type and content_type and not content_type.startswith(mime_type):
                    logger.warning("MIME type mismatch. Expected: %s, Got: %s", mime_type, content_type)

                # Save the file in chunks like the original script
                logger.debug("Writing file to %s", output_path)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content():
                        f.write(chunk)

            logger.debug("Successfully downloaded file to %s", output_path)
            return True

        except (requests.RequestException, OSError) as e:
            logger.error("Error downloading file (attempt %d/%d): %s", attempt+1, max_retries+1, e)
            if 'response' in locals():
                logger.debug("Response headers: %s", dict(response.headers) if hasattr(response, 'headers') else 'No headers')
                logger.debug("Response content: %s", response.text[:200] if hasattr(response, 'text') else 'No content')

            if attempt < max_retries:
                delay = attempt + 1  # Incremental backoff
                logger.info("Retrying download in %d seconds...", delay)
                time.sleep(delay)
            else:
                logger.error("Download failed after %d attempts", max_retries+1)
                return False

def download_media(media_data, download_dir, api_key=None):
    """Download an image or video and return its file path."""
    media_id = media_data.get("id")
    media_name = media_data.get("name", f"media-{media_id}")
    media_url = media_data.get("url")
    mime_type = media_data.get("mimeType", "image/jpeg")

    if not media_url:
        logger.error("No URL found for media %s", media_id)
        return None

    # Sanitize filename and add proper extension
    base_name = sanitize_filename(media_name)
    base_name, _ = os.path.splitext(base_name)  # Remove any existing extension
    extension = get_file_extension(mime_type)
    file_name = f"{base_name}{extension}"

    # Full path for the file
    file_path = Path(download_dir) / file_name

    # Skip if file already exists
    if file_path.exists():
        logger.info("File already exists: %s", file_path)
        return file_path

    # Download the file
    success = download_file(
        media_url,
        file_path,
        mime_type=mime_type,
        max_retries=config.get('max_retries', 3),
        api_key=api_key
    )

    if success:
        return file_path  # Return Path object
    else:
        return None

def save_metadata(metadata, file_path):
    """Save metadata to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("Saved metadata to %s", file_path)
        return True
    except Exception as e:
        logger.error("Error saving metadata to %s: %s", file_path, e)
        return False
