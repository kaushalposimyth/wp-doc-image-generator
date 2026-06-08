# WP Doc Featured Image Generator

Automatically generate branded featured images for WordPress documentation pages.

Given any WordPress doc URL, the tool:
1. Fetches the page title and category via the WordPress REST API
2. Generates a featured image matching your brand design (dark navy background, category badge, centred title, logos)
3. Optionally uploads it directly as the page's featured image — no manual steps

---

## Design Output

```
┌────────────────────────────────────────────────────────┐
│  [wdesignkit logo]                   [POSIMYTH logo]   │
│                                                        │
│                  ╔══════════════╗                      │
│                  ║ Getting      ║  ← green pill badge  │
│                  ║ Started      ║                      │
│                  ╚══════════════╝                      │
│                                                        │
│        How to Get Key for WDesignKit Activation?       │
└────────────────────────────────────────────────────────┘
          1200 × 630 px  ·  PNG  ·  auto-wrapped title
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download fonts (run once)
python generator.py --download-fonts

# 3. Copy and fill in your credentials
cp .env.example .env
# Edit .env with WORDPRESS_URL, WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD

# 4. Generate image for a doc page
python generator.py https://wdesignkit.com/docs/how-to-get-license-key/

# 5. Generate AND set as featured image automatically
python generator.py https://wdesignkit.com/docs/how-to-get-license-key/ --upload
```

---

## Usage

```
python generator.py [URL ...] [options]
```

| Option | Description |
|--------|-------------|
| `URL` | WordPress page/post URL or numeric post ID |
| `--upload` / `-u` | Upload generated image and set as WordPress featured image |
| `--preview` / `-p` | Open image preview without saving or uploading |
| `--output PATH` / `-o` | Custom output file path (single URL only) |
| `--category TEXT` / `-c` | Override the badge text (e.g. `"Getting Started"`) |
| `--font-size N` | Title font size in px — default 64, auto-shrinks for long titles |
| `--bulk FILE` / `-b` | Text file with one URL per line |
| `--report FILE` / `-r` | Save a JSON report of all processed pages |
| `--wp-url URL` | Override `WORDPRESS_URL` from the command line |
| `--download-fonts` | Download Inter font files to `assets/fonts/` |

---

## Bulk Processing

Create a file `urls.txt`:
```
https://wdesignkit.com/docs/page-one/
https://wdesignkit.com/docs/page-two/
https://wdesignkit.com/docs/page-three/
```

Then run:
```bash
python generator.py --bulk urls.txt --upload
```

---

## Configuration

### `.env` file

```env
WORDPRESS_URL=https://yoursite.com
WORDPRESS_USERNAME=your_username
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

Generate an Application Password at:  
`WordPress Admin → Users → Your Profile → Application Passwords`

### Design Customisation (`modules/image_builder.py`)

Edit the `DESIGN` dict at the top of `modules/image_builder.py`:

| Token | Default | Description |
|-------|---------|-------------|
| `width` / `height` | 1200 / 630 | Canvas size in px |
| `bg_color_top_left` | `(11, 19, 84)` | Background gradient start |
| `bg_color_bottom_right` | `(20, 34, 130)` | Background gradient end |
| `badge_bg` | `(52, 199, 89)` | Category badge colour |
| `badge_radius` | 50 | Badge corner radius |
| `logo_height` | 46 | Logo height in px |
| `title_font_size` | 64 | Starting title font size |

### Logo Customisation (`modules/logo_fetcher.py`)

Add your own brand logos to the `BRAND_LOGOS` dict:

```python
BRAND_LOGOS["mybrand"] = {
    "url": "https://yoursite.com/logo-white.png",
    "fallback_text": "MyBrand",
    "fallback_color": "#FFFFFF",
}
```

Then use `--left-brand mybrand` (or pass `left_brand="mybrand"` to the Python API).

---

## Project Structure

```
wp-doc-image-generator/
├── generator.py          ← main CLI
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── modules/
│   ├── wp_client.py      ← WordPress REST API (fetch metadata, upload media)
│   ├── image_builder.py  ← Pillow image generation engine
│   ├── logo_fetcher.py   ← logo download and cache
│   └── font_manager.py   ← Inter font downloader
├── assets/
│   └── fonts/            ← Inter TTF files (auto-downloaded)
├── cache/                ← cached logo images
└── output/               ← generated PNG files
```

---

## Python API

```python
from modules.wp_client import WPClient
from modules.image_builder import build_featured_image, build_from_page_info

# Fetch page metadata
client = WPClient()
page_info = client.get_page_info("https://yoursite.com/docs/some-page/")
# → { "title": "...", "category": "...", "post_id": 123, ... }

# Generate image
img = build_from_page_info(page_info, output_path="output/image.png")

# Or build directly
img = build_featured_image(
    title="How to Get License Key for WDesignKit Activation?",
    category="Getting Started",
    output_path="output/image.png",
    left_brand="wdesignkit",
    right_brand="posimyth",
)

# Upload as featured image
result = client.upload_and_set_featured(
    post_id=page_info["post_id"],
    image_path="output/image.png",
    title=page_info["title"],
    post_type=page_info["post_type"],
)
```

---

## Requirements

- Python 3.10+
- Internet connection (for first-time font and logo download)
- WordPress Application Password with Editor or higher permissions

---

## License

MIT
