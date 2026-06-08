"""
Logo fetcher and cache manager.
Downloads logos from WordPress sites (or known CDN URLs) and caches them locally.
Falls back to text rendering when logos cannot be fetched.
"""

import os
import hashlib
import requests
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Known logo URLs per brand — extend as needed
BRAND_LOGOS: dict[str, dict] = {
    "wdesignkit": {
        "url": "https://api.wdesignkit.com/images/website/common/wdesignkit.png",
        "fallback_text": "wdesignkit",
        "fallback_color": "#FFFFFF",
    },
    "posimyth": {
        # Full horizontal wordmark (1000×184 px)
        "url": "https://posimyth.com/wp-content/uploads/2023/01/new_posimyth_innovation_logo.png",
        "fallback_text": "POSIMYTH",
        "fallback_color": "#FFFFFF",
    },
    "nexter": {
        # Nexter logo from WDesignKit CDN
        "url": "https://api.wdesignkit.com/images/website/front/home/nexter-logo.webp",
        "fallback_text": "Nexter",
        "fallback_color": "#FFFFFF",
    },
    "tpae": {
        "url": "https://posimyth.com/wp-content/uploads/2025/06/theplusaddons.png",
        "fallback_text": "The Plus Addons",
        "fallback_color": "#FFFFFF",
    },
}


def _cache_path(url: str) -> Path:
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = url.split(".")[-1].split("?")[0]
    if ext not in ("png", "jpg", "jpeg", "svg", "webp"):
        ext = "png"
    return CACHE_DIR / f"{h}.{ext}"


def fetch_logo(
    brand: str,
    custom_url: Optional[str] = None,
    force_refresh: bool = False,
    timeout: int = 10,
) -> Optional[Path]:
    """
    Download and cache a brand logo. Returns local Path or None if unavailable.

    Args:
        brand: Brand key ("wdesignkit", "posimyth", etc.)
        custom_url: Override the default URL for this brand
        force_refresh: Re-download even if cached
        timeout: Request timeout in seconds
    """
    brand_cfg = BRAND_LOGOS.get(brand.lower(), {})
    url = custom_url or brand_cfg.get("url", "")

    if not url:
        return None

    cached = _cache_path(url)
    if cached.exists() and not force_refresh:
        return cached

    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        with open(cached, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return cached
    except Exception as e:
        print(f"  [warn] Could not fetch logo for '{brand}' from {url}: {e}")
        return None


def get_fallback_text(brand: str) -> tuple[str, str]:
    """Returns (text, hex_color) for text-based logo fallback."""
    cfg = BRAND_LOGOS.get(brand.lower(), {})
    return cfg.get("fallback_text", brand.upper()), cfg.get("fallback_color", "#FFFFFF")


def fetch_favicon_as_logo(site_url: str, timeout: int = 8) -> Optional[Path]:
    """
    Attempt to grab a site's favicon/apple-touch-icon as a last-resort logo.
    """
    site_url = site_url.rstrip("/")
    candidates = [
        f"{site_url}/apple-touch-icon.png",
        f"{site_url}/favicon-32x32.png",
        f"{site_url}/favicon.ico",
    ]
    for url in candidates:
        cached = _cache_path(url)
        if cached.exists():
            return cached
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.ok and len(resp.content) > 100:
                with open(cached, "wb") as f:
                    f.write(resp.content)
                return cached
        except Exception:
            continue
    return None
