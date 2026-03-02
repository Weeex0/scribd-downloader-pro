# Changelog

All notable changes to this project will be documented here.

---

## [1.0.0] - 2026-03-02

### Added
- First public release
- Embed-mode loading (`/embeds/{id}/content`) — clean document view with no UI chrome
- Precise page element capture using `div[id^='outer_page_']` selector
- Strip-stitch algorithm for pages taller than the viewport
- Auto-extraction of Scribd access key from page HTML
- Cookie authentication support (Cookie-Editor JSON format)
- sameSite cookie normalization — no more Playwright warnings
- `--images-only` mode to save pages as individual JPEGs
- PDF assembly using PyMuPDF with correct page dimensions
- CSS injection to remove all Scribd UI before capture
