"""
Font manager — downloads Inter from the official GitHub release zip and caches TTFs locally.
Falls back to Pillow's built-in bitmap font if download fails.
"""

import io
import zipfile
import requests
from pathlib import Path
from typing import Optional

FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Official Inter release (MIT / OFL licence)
INTER_RELEASE_URL = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"

# Which TTFs to extract from extras/ttf/ inside the zip
VARIANTS = {
    "Inter-Regular":  "extras/ttf/Inter-Regular.ttf",
    "Inter-Medium":   "extras/ttf/Inter-Medium.ttf",
    "Inter-SemiBold": "extras/ttf/Inter-SemiBold.ttf",
    "Inter-Bold":     "extras/ttf/Inter-Bold.ttf",
    "Inter-ExtraBold":"extras/ttf/Inter-ExtraBold.ttf",
}


def _font_path(name: str) -> Path:
    return FONTS_DIR / f"{name}.ttf"


def _all_present() -> bool:
    return all(_font_path(n).exists() and _font_path(n).stat().st_size > 1000 for n in VARIANTS)


def ensure_fonts(force: bool = False, timeout: int = 60) -> dict[str, Optional[Path]]:
    """
    Download and extract Inter font TTFs from the GitHub release zip.
    Skips if all fonts are already cached unless force=True.
    Returns {variant_name: Path or None}.
    """
    if _all_present() and not force:
        return {n: _font_path(n) for n in VARIANTS}

    print(f"  Downloading Inter fonts from GitHub release...")
    try:
        resp = requests.get(INTER_RELEASE_URL, timeout=timeout, stream=True)
        resp.raise_for_status()
        raw = resp.content
    except Exception as e:
        print(f"  [warn] Could not download Inter font zip: {e}")
        return {n: _font_path(n) if _font_path(n).exists() else None for n in VARIANTS}

    result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for name, zip_path in VARIANTS.items():
            dest = _font_path(name)
            try:
                data = zf.read(zip_path)
                dest.write_bytes(data)
                print(f"  [OK] {name}.ttf ({len(data) // 1024} KB)")
                result[name] = dest
            except KeyError:
                print(f"  [warn] {zip_path} not found in zip")
                result[name] = dest if dest.exists() else None

    return result


def get_font_path(variant: str = "Inter-Bold") -> Optional[Path]:
    """Return path to a font TTF, downloading if not cached."""
    dest = _font_path(variant)
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    # Download full zip to get this font
    fonts = ensure_fonts()
    return fonts.get(variant)


def get_pillow_font(variant: str = "Inter-Bold", size: int = 48):
    """Return a Pillow ImageFont, falling back to default if TTF unavailable."""
    from PIL import ImageFont
    path = get_font_path(variant)
    if path and path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception as e:
            print(f"  [warn] Could not load TTF {path}: {e}")
    # Pillow built-in bitmap font — no size control, but always works
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()
