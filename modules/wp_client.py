"""
WordPress REST API client.
Fetches page/post metadata (title, categories, tags, featured image)
and uploads generated images as new featured media.
"""

import os
import re
import json
import mimetypes
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class WPClient:
    def __init__(
        self,
        site_url: Optional[str] = None,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        self.site_url = (site_url or os.getenv("WORDPRESS_URL", "")).rstrip("/")
        self.username = username or os.getenv("WORDPRESS_USERNAME")
        self.app_password = app_password or os.getenv("WORDPRESS_APP_PASSWORD")

        if not self.site_url:
            raise ValueError("WORDPRESS_URL is not set. Add it to your .env file.")

        self.api = f"{self.site_url}/wp-json/wp/v2"
        self.session = requests.Session()
        if self.username and self.app_password:
            self.session.auth = (self.username, self.app_password)
        self.session.headers["User-Agent"] = "WPDocImageGenerator/1.0"

    # ── Resolve URL → post data ───────────────────────────────────────────────

    def _slug_from_url(self, url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        return path.split("/")[-1]

    def fetch_by_url(self, url: str) -> dict:
        slug = self._slug_from_url(url)
        for post_type in ("pages", "posts"):
            resp = self.session.get(
                f"{self.api}/{post_type}",
                params={"slug": slug, "_embed": 1},
                timeout=15,
            )
            if resp.ok:
                items = resp.json()
                if items:
                    return items[0]
        raise ValueError(
            f"Could not find page/post with slug '{slug}' on {self.site_url}.\n"
            "Check the URL and ensure the site is reachable."
        )

    def fetch_by_id(self, post_id: int) -> dict:
        for post_type in ("pages", "posts"):
            resp = self.session.get(
                f"{self.api}/{post_type}/{post_id}",
                params={"_embed": 1},
                timeout=15,
            )
            if resp.ok:
                return resp.json()
        raise ValueError(f"Post ID {post_id} not found.")

    def fetch(self, url_or_id: str) -> dict:
        url_or_id = url_or_id.strip()
        if url_or_id.startswith("http"):
            return self.fetch_by_url(url_or_id)
        if url_or_id.isdigit():
            return self.fetch_by_id(int(url_or_id))
        return self.fetch_by_url(f"{self.site_url}/{url_or_id}/")

    # ── Extract structured info ───────────────────────────────────────────────

    def get_page_info(self, url_or_id: str) -> dict:
        """
        Returns a clean dict with everything the image builder needs:
          title, category, tags, post_id, post_type, url, featured_image_url
        """
        post = self.fetch(url_or_id)

        title = post.get("title", {}).get("rendered", "")
        # Strip HTML tags from title
        title = re.sub(r"<[^>]+>", "", title).strip()

        # Resolve categories from _embedded
        categories = []
        embedded = post.get("_embedded", {})
        for term_list in embedded.get("wp:term", []):
            for term in term_list:
                if term.get("taxonomy") in ("category", "doc-category", "tutorials-cat"):
                    categories.append(term.get("name", ""))

        # Fallback: resolve category IDs manually
        if not categories:
            cat_ids = post.get("categories", [])
            for cid in cat_ids[:3]:
                r = self.session.get(f"{self.api}/categories/{cid}", timeout=10)
                if r.ok:
                    categories.append(r.json().get("name", ""))

        # Featured image URL
        featured_image_url = ""
        if "_embedded" in post:
            fi = embedded.get("wp:featuredmedia", [{}])
            if fi:
                featured_image_url = fi[0].get("source_url", "")

        post_type = "pages" if post.get("type", "page") == "page" else "posts"

        return {
            "post_id": post["id"],
            "post_type": post_type,
            "url": post.get("link", ""),
            "title": title,
            "category": categories[0] if categories else "Documentation",
            "all_categories": categories,
            "featured_image_url": featured_image_url,
            "featured_media_id": post.get("featured_media", 0),
        }

    # ── Upload image ──────────────────────────────────────────────────────────

    def upload_image(self, image_path: str, title: str = "") -> dict:
        """Upload an image file to WordPress media library. Returns media object."""
        if not self.username or not self.app_password:
            raise ValueError(
                "WORDPRESS_USERNAME and WORDPRESS_APP_PASSWORD are required to upload images."
            )

        path = Path(image_path)
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "image/png"

        with open(path, "rb") as f:
            resp = self.session.post(
                f"{self.api}/media",
                headers={
                    "Content-Disposition": f'attachment; filename="{path.name}"',
                    "Content-Type": mime_type,
                },
                data=f.read(),
                timeout=30,
            )

        if not resp.ok:
            raise RuntimeError(
                f"Upload failed ({resp.status_code}): {resp.text[:300]}"
            )

        media = resp.json()

        # Update alt text / title
        if title:
            self.session.post(
                f"{self.api}/media/{media['id']}",
                json={"title": title, "alt_text": title},
                timeout=15,
            )

        return media

    def set_featured_image(self, post_id: int, media_id: int, post_type: str = "pages") -> dict:
        """Set an uploaded media item as the featured image of a post/page."""
        resp = self.session.post(
            f"{self.api}/{post_type}/{post_id}",
            json={"featured_media": media_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def upload_and_set_featured(
        self, post_id: int, image_path: str, title: str = "", post_type: str = "pages"
    ) -> dict:
        """Upload image and immediately set it as the post's featured image."""
        media = self.upload_image(image_path, title=title)
        media_id = media["id"]
        self.set_featured_image(post_id, media_id, post_type=post_type)
        return {
            "media_id": media_id,
            "media_url": media.get("source_url", ""),
            "post_id": post_id,
        }

    # ── Download existing featured image ──────────────────────────────────────

    def download_image(self, image_url: str, dest_path: str) -> str:
        resp = self.session.get(image_url, timeout=20, stream=True)
        resp.raise_for_status()
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return dest_path
