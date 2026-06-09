# Changelog

All notable changes to the WP Doc Image Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

_Upcoming changes to be released in the next version._

---

## [v1.0.0] - 1 day ago (June 8, 2026)

### Added
- Initial release of WP Doc Featured Image Generator
- Fetch WordPress doc page title and category via REST API
- Generate branded featured images with:
  - Dark navy background design
  - Category badge (colored pill-shaped)
  - Centered, auto-wrapped title
  - Brand logos (wdesignkit + POSIMYTH)
- 1200 × 630 px PNG image output
- Optional auto-upload as featured image to WordPress
- Custom category override support (`--category` flag)
- Custom output filename support (`--output` flag)
- Preview-only mode (`--preview` flag)
- Bulk processing from text file (`--bulk urls.txt`)
- Font management system with automatic download
- Environment-based configuration (.env)
- Full CLI documentation and usage examples

### Features
- **image_builder.py**: Core image generation with PIL
- **wp_client.py**: WordPress REST API integration
- **logo_fetcher.py**: Logo management and positioning
- **font_manager.py**: Font handling and caching
- **generator.py**: Main CLI entry point
- Full error handling and user feedback
- Cache system for performance

---

## Versioning Guide

### How to Update This Changelog

1. **For new features/fixes**: Add entries under the `[Unreleased]` section
2. **When releasing**: Create a new version header with format `## [vX.Y.Z] - {relative_date} (YYYY-MM-DD)`
3. **Version numbers**:
   - `PATCH` (v1.0.1): Bug fixes and minor updates
   - `MINOR` (v1.1.0): New features (backward compatible)
   - `MAJOR` (v2.0.0): Breaking changes

4. **Relative dates**: Use natural language
   - "today" / "just now"
   - "1 day ago"
   - "4 days ago"
   - "next week"
   - Combine with full date: `- 1 day ago (June 9, 2026)`

### Sections to Use
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

### Optional: Auto-Update Script

To automatically update relative dates, add this script to your workflow:
```bash
# This would be called before committing
python scripts/update_changelog.py --version v1.0.1 --message "Bug fix"
```

---

## Release History

| Version | Date | Status |
|---------|------|--------|
| v1.0.0 | June 8, 2026 | Released |

