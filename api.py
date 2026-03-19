"""CivitAI API client for fetching collections, posts, images, and metadata."""

import json
import logging
from urllib.parse import quote
import requests

from config import config

logger = logging.getLogger(__name__)

class CivitaiAPI:
    """Client for interacting with CivitAI's TRPC API."""

    BASE_URL = "https://civitai.com/api/trpc"

    def __init__(self, api_key=None):
        """Initialize the API client with the provided API key."""
        self.api_key = api_key or config.get('api_key')

        # Check if API key is available
        if not self.api_key:
            logger.error("No API key found! Please make sure you have set your API key in the configuration.")
            self.headers = {}  # Empty headers if no API key
        else:
            # Simple authorization header, exactly like the original script
            self.headers = {'Authorization': 'Bearer ' + self.api_key}

    def get_collection_by_id(self, collection_id):
        """Get details of a collection by its ID."""
        logger.info("Fetching collection with ID: %s", collection_id)

        # Create request data
        request_data = {
            "json": {
                "id": int(collection_id),
                "authed": True
            }
        }

        # Encode parameters
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/collection.getById?input={encoded_input}"

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            return result.get("result", {}).get("data", {}).get("json")
        except Exception as e:
            logger.error("Error fetching collection %s: %s", collection_id, e)
            return None

    def get_images_in_collection(self, collection_id, cursor=None):
        """Get images in a collection with pagination support."""
        # Create the request data exactly like the working script
        request_data = {
            "json": {
                "collectionId": int(collection_id),
                "period": "AllTime",
                "sort": "Newest",
                "browsingLevel": 31,  # 31 = 1(PG) + 2(PG-13) + 4(R) + 8(X) + 16(XXX)
                "include": ["cosmetics"],
                "cursor": cursor,
                "authed": True
            }
        }

        # Add meta field only for the first request (when cursor is None)
        if cursor is None:
            request_data["meta"] = {"values": {"cursor": ["undefined"]}}

        # Construct the URL exactly like the working script
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/image.getInfinite?input={encoded_input}"

        logger.info("Fetching images in collection %s%s", collection_id, ' with cursor' if cursor else '')
        logger.debug("Request URL: %s", url)
        logger.debug("Request headers: %s", self.headers)
        logger.debug("Request data: %s", request_data)

        try:
            # Make direct request with just the authorization header
            logger.debug("Sending request to CivitAI API...")
            response = requests.get(url, headers=self.headers, timeout=30)

            logger.debug("Response status code: %s", response.status_code)
            response.raise_for_status()

            result = response.json()
            logger.debug("Response received: %s", result.keys())

            # Extract the data
            items = result.get('result', {}).get('data', {}).get('json', {}).get('items', [])
            next_cursor = result.get('result', {}).get('data', {}).get('json', {}).get('nextCursor')

            logger.debug("Retrieved %s items, next cursor: %s", len(items), next_cursor)

            return {
                "items": items,
                "nextCursor": next_cursor
            }

        except Exception as e:
            logger.error("Error fetching images from collection %s: %s", collection_id, e)
            if 'response' in locals():
                logger.error("Response status: %s", response.status_code)
                logger.error("Response content: %s", response.text[:500])
            return {"items": [], "nextCursor": None}

    def get_all_images_in_collection(self, collection_id):
        """Get all images in a collection by handling pagination."""
        all_images = []
        cursor = None
        batch_count = 0

        logger.info("Starting retrieval of all images from collection %s", collection_id)

        while True:
            batch_count += 1
            logger.debug("Retrieving batch #%s of images...", batch_count)

            result = self.get_images_in_collection(collection_id, cursor)
            if not result or not result.get("items"):
                if not all_images:  # No images retrieved at all
                    logger.error("No images found in collection %s", collection_id)
                break

            batch_items = result.get("items", [])
            logger.debug("Retrieved batch of %s images from collection %s", len(batch_items), collection_id)

            # Log some details about the first few items
            if batch_items and len(batch_items) > 0 and batch_count == 1:
                first_item = batch_items[0]
                logger.debug("First item sample - ID: %s, Name: %s, URL: %s", first_item.get('id'), first_item.get('name'), first_item.get('url'))

            all_images.extend(batch_items)

            cursor = result.get("nextCursor")
            logger.debug("Next cursor: %s", cursor)

            if not cursor:
                logger.debug("No more pages to retrieve")
                break

        logger.info("Retrieved a total of %s images from collection %s", len(all_images), collection_id)
        return all_images

    def get_posts_in_collection(self, collection_id, cursor=None):
        """Get posts in a collection with pagination support."""
        request_data = {
            "json": {
                "collectionId": int(collection_id),
                "period": "AllTime",
                "sort": "Newest",
                "cursor": cursor,
                "authed": True
            }
        }

        if cursor is None:
            request_data["meta"] = {"values": {"cursor": ["undefined"]}}

        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/post.getInfinite?input={encoded_input}"

        logger.info("Fetching posts in collection %s%s", collection_id, ' with cursor' if cursor else '')

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            items = result.get('result', {}).get('data', {}).get('json', {}).get('items', [])
            next_cursor = result.get('result', {}).get('data', {}).get('json', {}).get('nextCursor')

            logger.debug("Retrieved %s posts, next cursor: %s", len(items), next_cursor)
            return {
                "items": items,
                "nextCursor": next_cursor
            }
        except Exception as e:
            logger.error("Error fetching posts from collection %s: %s", collection_id, e)
            if 'response' in locals():
                logger.error("Response status: %s", response.status_code)
                logger.error("Response content: %s", response.text[:500])
            return {"items": [], "nextCursor": None}

    def get_all_posts_in_collection(self, collection_id):
        """Get all posts in a collection by handling pagination."""
        all_posts = []
        cursor = None

        logger.info("Starting retrieval of all posts from collection %s", collection_id)

        while True:
            result = self.get_posts_in_collection(collection_id, cursor)
            if not result or not result.get("items"):
                if not all_posts:
                    logger.error("No posts found in collection %s", collection_id)
                break

            all_posts.extend(result.get("items", []))
            cursor = result.get("nextCursor")

            if not cursor:
                break

        logger.info("Retrieved a total of %s posts from collection %s", len(all_posts), collection_id)
        return all_posts

    def get_post_by_id(self, post_id):
        """Get details of a post by its ID."""
        logger.info("Fetching post with ID: %s", post_id)

        # Create request data
        request_data = {
            "json": {
                "id": int(post_id),
                "authed": True
            }
        }

        # Encode parameters
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/post.get?input={encoded_input}"

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            return result.get("result", {}).get("data", {}).get("json")
        except Exception as e:
            logger.error("Error fetching post %s: %s", post_id, e)
            return None

    def get_images_in_post(self, post_id, cursor=None):
        """Get images in a post with pagination support."""
        # Create the request data
        request_data = {
            "json": {
                "postId": int(post_id),
                "browsingLevel": 31,  # 31 = 1(PG) + 2(PG-13) + 4(R) + 8(X) + 16(XXX)
                "cursor": cursor,
                "authed": True
            }
        }

        # Add meta field only for the first request (when cursor is None)
        if cursor is None:
            request_data["meta"] = {"values": {"cursor": ["undefined"]}}

        # Construct the URL
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/image.getInfinite?input={encoded_input}"

        logger.info("Fetching images in post %s%s", post_id, ' with cursor' if cursor else '')

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Extract the data
            items = result.get('result', {}).get('data', {}).get('json', {}).get('items', [])
            next_cursor = result.get('result', {}).get('data', {}).get('json', {}).get('nextCursor')

            logger.debug("Retrieved %s images from post %s", len(items), post_id)

            return {
                "items": items,
                "nextCursor": next_cursor
            }

        except Exception as e:
            logger.error("Error fetching images from post %s: %s", post_id, e)
            return {"items": [], "nextCursor": None}

    def get_all_images_in_post(self, post_id):
        """Get all images in a post by handling pagination."""
        all_images = []
        cursor = None

        while True:
            result = self.get_images_in_post(post_id, cursor)
            if not result or not result.get("items"):
                break

            all_images.extend(result.get("items", []))
            cursor = result.get("nextCursor")

            if not cursor:
                break

            logger.debug("Retrieved %s images, continuing with next page", len(result['items']))

        logger.info("Retrieved a total of %s images from post %s", len(all_images), post_id)
        return all_images

    def get_image_details(self, image_id):
        """Get detailed information about an image or video."""
        logger.info("Fetching details for media ID: %s", image_id)

        # Create request data
        request_data = {
            "json": {
                "id": int(image_id),
                "authed": True
            }
        }

        # Encode parameters
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/image.get?input={encoded_input}"

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            return result.get("result", {}).get("data", {}).get("json")
        except Exception as e:
            logger.error("Error fetching image details %s: %s", image_id, e)
            return None

    def get_image_generation_data(self, image_id):
        """Get generation data for an image (prompts, models used, etc.)."""
        logger.info("Fetching generation data for media ID: %s", image_id)

        # Create request data
        request_data = {
            "json": {
                "id": int(image_id),
                "authed": True
            }
        }

        # Encode parameters
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/image.getGenerationData?input={encoded_input}"

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            return result.get("result", {}).get("data", {}).get("json")
        except Exception as e:
            logger.error("Error fetching generation data %s: %s", image_id, e)
            return None

    def get_image_tags(self, image_id):
        """Get tags for an image."""
        logger.info("Fetching tags for media ID: %s", image_id)

        # Create request data
        request_data = {
            "json": {
                "id": int(image_id),
                "type": "image",
                "authed": True
            }
        }

        # Encode parameters
        encoded_input = quote(json.dumps(request_data, separators=(',', ':')))
        url = f"{self.BASE_URL}/tag.getVotableTags?input={encoded_input}"

        try:
            # Make direct request with just the authorization header
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            return result.get("result", {}).get("data", {}).get("json")
        except Exception as e:
            logger.error("Error fetching tags %s: %s", image_id, e)
            return []

def extract_metadata(api, image_data):
    """Extract metadata from image data and related API responses."""
    image_id = image_data.get("id")

    # Basic metadata
    metadata = {
        "id": image_id,
        "name": image_data.get("name"),
        "width": image_data.get("width"),
        "height": image_data.get("height"),
        "mimeType": image_data.get("mimeType"),
        "hash": image_data.get("hash"),
        "nsfw_level": image_data.get("nsfwLevel"),
        "created_at": image_data.get("createdAt"),
        "published_at": image_data.get("publishedAt"),
        "url": image_data.get("url"),
        "user": None,
        "stats": None,
        "generation_data": None,
        "tags": []
    }

    # Add user info if available
    if "user" in image_data and image_data["user"]:
        metadata["user"] = {
            "id": image_data["user"].get("id"),
            "username": image_data["user"].get("username")
        }

    # Add stats if available
    if "stats" in image_data and image_data["stats"]:
        metadata["stats"] = image_data["stats"]

    # Fetch additional metadata
    try:
        # Get generation data (prompts, models used, etc.)
        gen_data = api.get_image_generation_data(image_id)
        if gen_data:
            metadata["generation_data"] = gen_data

            # Extract prompts if available
            if gen_data.get("meta") and "prompt" in gen_data["meta"]:
                metadata["prompt"] = gen_data["meta"]["prompt"]
            if gen_data.get("meta") and "negativePrompt" in gen_data["meta"]:
                metadata["negative_prompt"] = gen_data["meta"]["negativePrompt"]

            # Extract model information if available
            if gen_data.get("resources"):
                metadata["models"] = gen_data["resources"]

        # Get tags
        tags = api.get_image_tags(image_id)
        if tags:
            metadata["tags"] = [{"id": tag.get("id"), "name": tag.get("name")} for tag in tags]

    except Exception as e:
        logger.error("Error fetching additional metadata for media %s: %s", image_id, e)

    return metadata

def create_collection_metadata(api, collection_id, images_metadata):
    """Create a metadata object for a collection."""
    collection = api.get_collection_by_id(collection_id)
    if not collection:
        logger.error("Failed to get collection data for ID: %s", collection_id)
        return {
            "id": collection_id,
            "name": f"Collection-{collection_id}",
            "media_count": len(images_metadata),
            "media": images_metadata
        }

    # Extract collection data from the response
    collection_data = collection.get("collection", {})

    collection_meta = {
        "id": collection_data.get("id", collection_id),
        "name": collection_data.get("name", f"Collection-{collection_id}"),
        "description": collection_data.get("description", ""),
        "type": collection_data.get("type"),
        "nsfw": collection_data.get("nsfw"),
        "nsfwLevel": collection_data.get("nsfwLevel"),
        "created_at": collection_data.get("createdAt"),
        "user": {
            "id": collection_data.get("user", {}).get("id"),
            "username": collection_data.get("user", {}).get("username")
        },
        "media_count": len(images_metadata),
        "media": images_metadata
    }

    return collection_meta
