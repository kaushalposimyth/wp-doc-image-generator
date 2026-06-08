"""
Featured image builder.

Replicates the WDesignKit/POSIMYTH documentation featured image design:

  ┌────────────────────────────────────────────────┐
  │  [wdesignkit logo]         [POSIMYTH logo]     │  ← dark navy bg
  │                                                │
  │              ╔══════════════╗                  │
  │              ║ Getting      ║  ← green pill    │
  │              ║ Started      ║                  │
  │              ╚══════════════╝                  │
  │                                                │
  │      How to Get Key for WDesignKit             │  ← white bold
  │              Activation?                       │
  └────────────────────────────────────────────────┘

Output: PNG, default 1200×630 px (standard OG image / WP featured image size).
"""

import textwrap
import math
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .font_manager import get_pillow_font
from .logo_fetcher import fetch_logo, get_fallback_text


# ── Design tokens ─────────────────────────────────────────────────────────────

DESIGN = {
    # Canvas
    "width": 1200,
    "height": 630,

    # Background gradient: top-left deep navy → bottom-right slightly lighter navy
    "bg_color_top_left":     (11, 19, 84),    # #0B1354
    "bg_color_bottom_right": (20, 34, 130),   # #142282

    # Category badge
    "badge_bg":        (52, 199, 89),   # #34C759  green
    "badge_text":      (255, 255, 255), # white
    "badge_padding_x": 32,
    "badge_padding_y": 12,
    "badge_radius":    50,              # fully rounded pill

    # Title
    "title_color":    (255, 255, 255),
    "title_max_width_ratio": 0.82,     # fraction of canvas width
    "title_line_spacing": 1.25,

    # Logos
    "logo_height":   46,               # px, logos are scaled to this height
    "logo_margin_x": 50,
    "logo_margin_y": 42,

    # Subtle radial glow in the centre
    "glow_color":  (30, 50, 180),
    "glow_radius": 320,

    # Thin bottom accent line
    "accent_color": (52, 199, 89),
    "accent_height": 5,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def _draw_gradient_bg(img: Image.Image):
    """Draw a diagonal gradient from top-left to bottom-right."""
    d = DESIGN
    w, h = img.size
    tl = d["bg_color_top_left"]
    br = d["bg_color_bottom_right"]
    px = img.load()
    diag = math.sqrt(w ** 2 + h ** 2)
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h)   # 0 → top-left, 1 → bottom-right
            r = int(tl[0] + (br[0] - tl[0]) * t)
            g = int(tl[1] + (br[1] - tl[1]) * t)
            b = int(tl[2] + (br[2] - tl[2]) * t)
            px[x, y] = (r, g, b, 255)


def _draw_radial_glow(img: Image.Image):
    """Soft centre glow overlay."""
    d = DESIGN
    w, h = img.size
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    cx, cy = w // 2, h // 2
    r = d["glow_radius"]
    gc = d["glow_color"]
    # Draw concentric circles with decreasing opacity
    steps = 40
    for i in range(steps, 0, -1):
        alpha = int(60 * (i / steps) ** 2)
        cr = int(r * i / steps)
        gd.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(*gc, alpha))
    # Blur for smooth glow
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=30))
    img.alpha_composite(glow_layer)


def _load_logo_image(brand: str, custom_url: Optional[str] = None) -> Optional[Image.Image]:
    """Fetch logo and return as RGBA PIL image, or None."""
    path = fetch_logo(brand, custom_url=custom_url)
    if path and path.exists():
        try:
            logo = Image.open(path).convert("RGBA")
            return logo
        except Exception as e:
            print(f"  [warn] Could not open logo {path}: {e}")
    return None


def _scale_logo(logo: Image.Image, target_height: int) -> Image.Image:
    ratio = target_height / logo.height
    new_w = int(logo.width * ratio)
    return logo.resize((new_w, target_height), Image.LANCZOS)


def _text_logo_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_title(title: str, font, max_width: int) -> list[str]:
    """Word-wrap title to fit within max_width pixels."""
    words = title.split()
    lines = []
    current = []

    # Temporary draw surface for measuring
    tmp = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(tmp)

    for word in words:
        test = " ".join(current + [word])
        bbox = d.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _get_text_height(font, text: str = "Ag") -> int:
    tmp = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


# ── Main builder ──────────────────────────────────────────────────────────────

def build_featured_image(
    title: str,
    category: str = "Documentation",
    output_path: Optional[str] = None,
    left_brand: str = "wdesignkit",
    right_brand: str = "posimyth",
    left_logo_url: Optional[str] = None,
    right_logo_url: Optional[str] = None,
    bg_color_override: Optional[tuple] = None,
    badge_color_override: Optional[tuple] = None,
    title_font_size: int = 64,
    category_font_size: int = 28,
) -> Image.Image:
    """
    Generate a featured image matching the WDesignKit doc design.

    Args:
        title:               Page/post title
        category:            Category label shown in the badge (e.g. "Getting Started")
        output_path:         If provided, saves PNG to this path
        left_brand:          Brand key for the left logo ("wdesignkit", "nexter", "tpae", …)
        right_brand:         Brand key for the right logo ("posimyth")
        left_logo_url:       Override URL for left logo
        right_logo_url:      Override URL for right logo
        bg_color_override:   Override background (R,G,B) tuple
        badge_color_override: Override badge colour (R,G,B) tuple
        title_font_size:     Starting font size for title (auto-shrinks if too large)
        category_font_size:  Font size for the category badge text

    Returns:
        PIL.Image in RGBA mode
    """
    d = DESIGN.copy()
    if bg_color_override:
        d["bg_color_top_left"] = bg_color_override
        d["bg_color_bottom_right"] = tuple(min(255, c + 30) for c in bg_color_override)
    if badge_color_override:
        d["badge_bg"] = badge_color_override

    w, h = d["width"], d["height"]

    # ── 1. Background ─────────────────────────────────────────────────────────
    img = Image.new("RGBA", (w, h), (*d["bg_color_top_left"], 255))
    _draw_gradient_bg(img)
    _draw_radial_glow(img)
    draw = ImageDraw.Draw(img)

    # ── 2. Bottom accent line ─────────────────────────────────────────────────
    draw.rectangle([0, h - d["accent_height"], w, h], fill=(*d["accent_bg"], 255) if "accent_bg" in d else (*d["badge_bg"], 255))

    # ── 3. Logos ──────────────────────────────────────────────────────────────
    logo_font = get_pillow_font("Inter-SemiBold", size=22)
    lh = d["logo_height"]
    mx, my = d["logo_margin_x"], d["logo_margin_y"]

    # Left logo
    left_logo_img = _load_logo_image(left_brand, custom_url=left_logo_url)
    if left_logo_img:
        left_logo_img = _scale_logo(left_logo_img, lh)
        img.alpha_composite(left_logo_img, (mx, my))
    else:
        fb_text, fb_color = get_fallback_text(left_brand)
        draw.text((mx, my + (lh - 22) // 2), fb_text, font=logo_font, fill=fb_color)

    # Right logo
    right_logo_img = _load_logo_image(right_brand, custom_url=right_logo_url)
    if right_logo_img:
        right_logo_img = _scale_logo(right_logo_img, lh)
        rx = w - mx - right_logo_img.width
        img.alpha_composite(right_logo_img, (rx, my))
    else:
        fb_text, fb_color = get_fallback_text(right_brand)
        fb_w = _text_logo_width(draw, fb_text, logo_font)
        draw.text((w - mx - fb_w, my + (lh - 22) // 2), fb_text, font=logo_font, fill=fb_color)

    # ── 4. Category badge ─────────────────────────────────────────────────────
    cat_font = get_pillow_font("Inter-SemiBold", size=category_font_size)
    cat_bbox = draw.textbbox((0, 0), category, font=cat_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    cat_h = cat_bbox[3] - cat_bbox[1]

    px, py = d["badge_padding_x"], d["badge_padding_y"]
    badge_w = cat_w + px * 2
    badge_h = cat_h + py * 2

    # Position: centred horizontally, upper-centre area
    bx = (w - badge_w) // 2
    by = h // 2 - badge_h - 50   # slightly above centre

    _draw_rounded_rect(draw, [bx, by, bx + badge_w, by + badge_h], d["badge_radius"], (*d["badge_bg"], 255))
    draw.text(
        (bx + px - cat_bbox[0], by + py - cat_bbox[1]),
        category,
        font=cat_font,
        fill=(*d["badge_text"], 255),
    )

    # ── 5. Title ───────────────────────────────────────────────────────────────
    max_title_w = int(w * d["title_max_width_ratio"])

    # Auto-shrink font until title fits in 3 lines
    font_size = title_font_size
    while font_size >= 28:
        title_font = get_pillow_font("Inter-Bold", size=font_size)
        lines = _wrap_title(title, title_font, max_title_w)
        if len(lines) <= 3:
            break
        font_size -= 4
    else:
        title_font = get_pillow_font("Inter-Bold", size=28)
        lines = _wrap_title(title, title_font, max_title_w)

    line_h = _get_text_height(title_font)
    spacing = int(line_h * (d["title_line_spacing"] - 1))
    block_h = len(lines) * line_h + (len(lines) - 1) * spacing

    # Start drawing just below the badge
    ty = by + badge_h + 32

    for line in lines:
        lbbox = draw.textbbox((0, 0), line, font=title_font)
        lw = lbbox[2] - lbbox[0]
        tx = (w - lw) // 2 - lbbox[0]
        draw.text((tx, ty - lbbox[1]), line, font=title_font, fill=(*d["title_color"], 255))
        ty += line_h + spacing

    # ── 6. Save ───────────────────────────────────────────────────────────────
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(str(out), "PNG", optimize=True)
        print(f"  [OK] Saved: {out}")

    return img


def build_from_page_info(page_info: dict, output_path: Optional[str] = None, **kwargs) -> Image.Image:
    """
    Convenience wrapper — pass the dict from WPClient.get_page_info() directly.
    Infers brand from category if possible.
    """
    title    = page_info.get("title", "")
    category = page_info.get("category", "Documentation")

    # Infer left brand from site URL
    url = page_info.get("url", "")
    if "wdesignkit" in url:
        left_brand = "wdesignkit"
    elif "nexter" in url or "nexterblocks" in url:
        left_brand = "nexter"
    elif "theplusaddons" in url or "plusaddons" in url:
        left_brand = "tpae"
    else:
        left_brand = kwargs.pop("left_brand", "wdesignkit")

    return build_featured_image(
        title=title,
        category=category,
        output_path=output_path,
        left_brand=left_brand,
        **kwargs,
    )
