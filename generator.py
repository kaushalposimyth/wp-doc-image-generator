#!/usr/bin/env python3
"""
WP Doc Featured Image Generator
================================
Fetches a WordPress documentation page by URL, extracts its title and category,
generates a branded featured image, and optionally uploads it directly to WordPress.

Usage examples
--------------
# Generate image and save locally (no upload)
python generator.py https://wdesignkit.com/docs/how-to-get-license-key/

# Generate AND auto-upload as featured image
python generator.py https://wdesignkit.com/docs/how-to-get-license-key/ --upload

# Override category text shown on badge
python generator.py <url> --category "Getting Started"

# Use a custom output filename
python generator.py <url> --output output/my-image.png

# Preview only (no save, no upload) — opens the image in your viewer
python generator.py <url> --preview

# Bulk: read URLs from a text file (one per line)
python generator.py --bulk urls.txt --upload

# Download fonts (run once, required first time)
python generator.py --download-fonts
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent / ".env.example"
load_dotenv(env_path)

from modules.wp_client import WPClient
from modules.image_builder import build_featured_image, build_from_page_info
from modules.font_manager import ensure_fonts


OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:80]


def output_filename(title: str) -> Path:
    return OUTPUT_DIR / f"{slugify(title)}.png"


def process_url(
    url: str,
    args,
    client: WPClient,
) -> dict:
    """
    Full pipeline for a single URL:
      1. Fetch page info from WordPress
      2. Generate featured image
      3. Optionally upload
      4. Return result dict
    """
    print(f"\n{'─' * 60}")
    print(f"URL      : {url}")

    # 1. Fetch metadata
    try:
        page_info = client.get_page_info(url)
    except Exception as e:
        print(f"[ERROR] Could not fetch page: {e}")
        return {"url": url, "status": "error", "error": str(e)}

    title    = page_info["title"]
    category = args.category or page_info["category"]

    print(f"Title    : {title}")
    print(f"Category : {category}")
    print(f"Post ID  : {page_info['post_id']}")

    # 2. Determine output path
    out_path = args.output if (hasattr(args, "output") and args.output and len(getattr(args, "urls", [])) <= 1) else str(output_filename(title))
    print(f"Output   : {out_path}")

    # 3. Generate image
    print("Generating image...")
    img = build_from_page_info(
        page_info,
        output_path=out_path if not args.preview else None,
        title_font_size=getattr(args, "font_size", 64),
    )

    # If preview-only, show and exit for this item
    if args.preview:
        img.show(title=title)
        return {"url": url, "status": "preview", "title": title}

    # 4. Upload
    result = {
        "url": url,
        "post_id": page_info["post_id"],
        "title": title,
        "category": category,
        "image_path": out_path,
        "status": "generated",
    }

    if args.upload:
        if not os.getenv("WORDPRESS_USERNAME") or not os.getenv("WORDPRESS_APP_PASSWORD"):
            print("[warn] WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD not set — skipping upload.")
        else:
            print("Uploading to WordPress...")
            try:
                upload_result = client.upload_and_set_featured(
                    post_id=page_info["post_id"],
                    image_path=out_path,
                    title=title,
                    post_type=page_info["post_type"],
                )
                result["media_id"]  = upload_result["media_id"]
                result["media_url"] = upload_result["media_url"]
                result["status"]    = "uploaded"
                print(f"  ✓ Featured image set (media ID: {upload_result['media_id']})")
                print(f"  ✓ Media URL: {upload_result['media_url']}")
            except Exception as e:
                print(f"  [ERROR] Upload failed: {e}")
                result["status"] = "upload_failed"
                result["error"]  = str(e)

    edit_url = f"{os.getenv('WORDPRESS_URL', '').rstrip('/')}/wp-admin/post.php?post={page_info['post_id']}&action=edit"
    result["edit_url"] = edit_url
    print(f"  Edit URL: {edit_url}")

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate WordPress documentation featured images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more WordPress page/post URLs (or IDs)",
    )
    parser.add_argument(
        "--bulk", "-b",
        metavar="FILE",
        help="Text file with one URL per line",
    )
    parser.add_argument(
        "--upload", "-u",
        action="store_true",
        help="Upload generated image as featured image in WordPress",
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Open image preview (do not save or upload)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="PATH",
        help="Output file path (single URL only)",
    )
    parser.add_argument(
        "--category", "-c",
        metavar="TEXT",
        help="Override the badge category text",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=64,
        help="Title font size in px (default: 64, auto-shrinks for long titles)",
    )
    parser.add_argument(
        "--download-fonts",
        action="store_true",
        help="Download Inter font files and exit",
    )
    parser.add_argument(
        "--report", "-r",
        metavar="FILE",
        help="Save JSON report of all processed pages",
    )
    parser.add_argument(
        "--wp-url",
        help="Override WORDPRESS_URL (instead of .env)",
    )

    args = parser.parse_args()

    # ── Font download mode ────────────────────────────────────────────────────
    if args.download_fonts:
        print("Downloading Inter fonts...")
        fonts = ensure_fonts(force=True)
        ok = sum(1 for v in fonts.values() if v)
        print(f"\n[OK] Downloaded {ok}/{len(fonts)} font variants to assets/fonts/")
        return

    # ── Build URL list ────────────────────────────────────────────────────────
    urls = list(args.urls or [])
    if args.bulk:
        bulk_path = Path(args.bulk)
        if not bulk_path.exists():
            print(f"[ERROR] Bulk file not found: {bulk_path}")
            sys.exit(1)
        for line in bulk_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    if not urls:
        parser.print_help()
        print("\n[ERROR] Provide at least one URL or use --bulk <file>")
        sys.exit(1)

    # ── WordPress client ──────────────────────────────────────────────────────
    if args.wp_url:
        os.environ["WORDPRESS_URL"] = args.wp_url

    try:
        client = WPClient()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("  Add WORDPRESS_URL to your .env file or pass --wp-url <url>")
        sys.exit(1)

    # ── Process each URL ──────────────────────────────────────────────────────
    print(f"Processing {len(urls)} page(s)...")
    results = []
    for url in urls:
        result = process_url(url, args, client)
        results.append(result)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"SUMMARY: {len(results)} page(s) processed")
    ok       = [r for r in results if r.get("status") in ("generated", "uploaded", "preview")]
    uploaded = [r for r in results if r.get("status") == "uploaded"]
    errors   = [r for r in results if r.get("status") == "error"]

    print(f"  ✓ Generated : {len(ok)}")
    if uploaded:
        print(f"  ✓ Uploaded  : {len(uploaded)}")
    if errors:
        print(f"  ✗ Errors    : {len(errors)}")
        for e in errors:
            print(f"      {e['url']} → {e.get('error', '')}")

    if not args.preview:
        print(f"\nImages saved to: {OUTPUT_DIR.resolve()}")

    # ── JSON report ───────────────────────────────────────────────────────────
    if args.report:
        report_path = Path(args.report)
        report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Report   : {report_path.resolve()}")


if __name__ == "__main__":
    main()
