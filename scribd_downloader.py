#!/usr/bin/env python3
"""
Scribd Downloader PRO — Embed + Element Mode
=============================================
Reverse-engineered from the Scribd Premium Downloader browser extension.

Key insight from the extension's content.js:
  - Embed URL: /embeds/{id}/content?start_page=1&view_mode=scroll&access_key=key-1
  - Page selector: div[id^='outer_page_']  (inside div.outer_page_container)
  - Strip-stitch: for pages taller than viewport, scroll in strips and stitch

INSTALL:
    pip install playwright pymupdf pillow requests
    playwright install chromium

USAGE:
    python scribd_downloader_pro.py <scribd_url> --cookies cookies.json
    python scribd_downloader_pro.py <scribd_url> --cookies cookies.json --images-only
"""

import os, re, sys, json, time, hashlib, argparse
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────
OUTPUT_DIR       = Path("scribd_output")
IMAGES_DIR       = OUTPUT_DIR / "images"
LOAD_WAIT        = 4.0       # seconds after embed loads
PAGE_SETTLE      = 0.9       # seconds after scrollIntoView (same as extension: 900ms)
STRIP_SETTLE     = 0.35      # seconds between strip scrolls
TIMEOUT          = 60000     # ms
MIN_SLIDE_BYTES  = 5_000
SCRIBD_COOKIE_STRING = ""

# CSS injected by the extension to clean up UI before capture
CLEAN_CSS = """
    .toolbar_drop, .global_header, .mobile_overlay,
    #scribd_c_wrapper, .promo_banner,
    .recommendations_sidebar, .sidebar,
    .ads, .ad, [class*='ad-'], iframe,
    .modal, .paywall, [class*='paywall'],
    [class*='subscribe'], [class*='banner'],
    .header, header, nav { display: none !important; }

    .document_scroller {
        overflow: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .outer_page_container {
        margin: 0 auto !important;
        padding: 0 !important;
        border: none !important;
        box-shadow: none !important;
    }
    body {
        background: #fff !important;
        overflow: hidden !important;
    }
"""

# ─── UTILITIES ───────────────────────────────────────────────────────────────
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def sanitize(name):
    name = re.sub(r"\s*\|.*$", "", name).strip()
    name = re.sub(r'[\\/*?:"<>|()\',;]', "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:200] or "scribd_document"

def img_hash(data):
    return hashlib.md5(data[:8192]).hexdigest()

_SS_MAP = {
    "no_restriction":"None","unspecified":"None",
    "lax":"Lax","strict":"Strict","none":"None",
}
def normalize_cookie(c):
    out = {
        "name":   c.get("name",   c.get("Name",   "")),
        "value":  c.get("value",  c.get("Value",  "")),
        "domain": c.get("domain", c.get("Domain", ".scribd.com")),
        "path":   c.get("path",   c.get("Path",   "/")),
    }
    exp = c.get("expirationDate", c.get("expires"))
    if exp:
        try: out["expires"] = int(float(exp))
        except: pass
    if "httpOnly" in c: out["httpOnly"] = bool(c["httpOnly"])
    if "secure"   in c: out["secure"]   = bool(c["secure"])
    raw_ss = str(c.get("sameSite", c.get("same_site", ""))).lower().strip()
    norm = _SS_MAP.get(raw_ss)
    if norm: out["sameSite"] = norm
    return out

def load_cookies_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return [normalize_cookie(c) for c in json.load(f)]

def parse_cookie_string(s):
    out = []
    for part in s.split(";"):
        part = part.strip()
        if "=" in part:
            n, _, v = part.partition("=")
            out.append(normalize_cookie({"name": n.strip(), "value": v.strip()}))
    return out

def safe_eval(page, expr, default=None):
    try:    return page.evaluate(expr)
    except: return default

def parse_scribd_url(url):
    """Extract (doc_id, access_key) from any Scribd URL."""
    from urllib.parse import urlparse, parse_qs
    p = urlparse(url)
    qs = parse_qs(p.query)
    access_key = qs.get("access_key", ["key-1"])[0]
    m = re.search(r"/(?:document|doc|embeds|read|book|audiobook)/(\d+)", url)
    doc_id = m.group(1) if m else None
    return doc_id, access_key

def build_embed_url(doc_id, access_key="key-1"):
    return (f"https://www.scribd.com/embeds/{doc_id}/content"
            f"?start_page=1&view_mode=scroll&access_key={access_key}")

# ─── MAIN SCRAPER ─────────────────────────────────────────────────────────────
def scrape_scribd(original_url, cookies, images_only):
    from playwright.sync_api import sync_playwright

    doc_id, access_key = parse_scribd_url(original_url)
    if not doc_id:
        print("✗ Cannot extract doc ID from URL.")
        sys.exit(1)

    # Try to extract a better access_key from the main page's JS
    print(f"📄 Doc ID: {doc_id}")

    page_images = {}   # page_num → bytes (final stitched image)
    title = f"scribd_{doc_id}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--window-size=1280,900",
                "--force-device-scale-factor=2",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # Add cookies individually (handles bad sameSite values)
        ok = 0
        for c in cookies:
            try:
                context.add_cookies([c])
                ok += 1
            except: pass
        if cookies:
            print(f"  🍪 Cookies: {ok}/{len(cookies)} added")

        pg = context.new_page()

        # ── Step 1: Load main doc page to get title + real access_key ──────
        print(f"\n🌐 Loading main page for title/access_key…")
        try:
            pg.goto(original_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            time.sleep(2)
            raw_title = safe_eval(pg, "document.title", "") or ""
            if raw_title:
                title = sanitize(raw_title)
                print(f"  📖 Title: {title}")
            html = safe_eval(pg, "document.documentElement.outerHTML", "") or ""
            for pat in [r'"access_key"\s*:\s*"([^"]{10,})"',
                        r'"accessKey"\s*:\s*"([^"]{10,})"']:
                m = re.search(pat, html)
                if m and m.group(1) != "key-1":
                    access_key = m.group(1)
                    print(f"  🔑 Real access_key found: {access_key[:25]}…")
                    break
        except Exception as e:
            print(f"  ⚠ Main page: {e}")

        # ── Step 2: Load the embed URL ──────────────────────────────────────
        embed_url = build_embed_url(doc_id, access_key)
        print(f"\n📺 Loading embed: {embed_url[:80]}…")
        try:
            pg.goto(embed_url, wait_until="domcontentloaded", timeout=TIMEOUT)
        except Exception as e:
            print(f"  ⚠ Embed load: {e}")

        time.sleep(LOAD_WAIT)

        # Inject clean CSS (same as the extension)
        safe_eval(pg, f"""
            (() => {{
                const s = document.createElement('style');
                s.id = 'spd-clean';
                s.textContent = `{CLEAN_CSS}`;
                document.head.appendChild(s);
            }})()
        """)

        # ── Step 3: Find pages using the EXACT extension selector ──────────
        # Extension uses: div.outer_page_container div[id^='outer_page_']
        pages = pg.query_selector_all("div[id^='outer_page_']")
        total = len(pages)
        print(f"\n📃 Found {total} page elements")

        if total == 0:
            # Fallback: scroll to trigger lazy load then retry
            print("  ↩ No pages yet — scrolling to trigger render…")
            scroll_h = safe_eval(pg, "document.documentElement.scrollHeight", 0) or 5000
            vp_h = (pg.viewport_size or {}).get("height", 900)
            y = 0
            while y < scroll_h:
                safe_eval(pg, f"window.scrollTo({{top:{y},behavior:'instant'}})")
                time.sleep(0.8)
                y += int(vp_h * 0.8)
                scroll_h = safe_eval(pg, "document.documentElement.scrollHeight", scroll_h) or scroll_h
            safe_eval(pg, "window.scrollTo({top:0,behavior:'instant'})")
            time.sleep(1)
            pages = pg.query_selector_all("div[id^='outer_page_']")
            total = len(pages)
            print(f"  📃 After scroll: {total} page elements")

        if total == 0:
            print("  ✗ No pages found. The embed may require authentication.")
            browser.close()
            return None, title, {"page_screenshots": {}, "jsonp_urls": [], "total_pages": 0}

        vp_h = (pg.viewport_size or {}).get("height", 900)
        vp_w = (pg.viewport_size or {}).get("width", 1280)

        # ── Step 4: Capture each page using strip-stitch ───────────────────
        # Mirrors the extension's captureVisibleTab + canvas stitching.
        # In Playwright we use element.screenshot() for strips.

        seen_hashes = set()

        for i, page_el in enumerate(pages):
            page_num = i + 1
            print(f"  📷 Page {page_num}/{total}", end="", flush=True)

            try:
                # Scroll page into view (extension: scrollIntoView block:'start')
                page_el.scroll_into_view_if_needed()
                safe_eval(pg, """
                    (el => el.scrollIntoView({behavior:'instant', block:'start'}))
                """)
                # Use evaluate to scroll the actual element
                pg.evaluate(
                    "(el) => el.scrollIntoView({behavior:'instant', block:'start'})",
                    page_el
                )
                time.sleep(PAGE_SETTLE)  # 900ms like the extension

                bb = page_el.bounding_box()
                if not bb:
                    print(" ✗ no bounding box")
                    continue

                page_w = bb["width"]
                page_h = bb["height"]

                if page_h <= 0 or page_w <= 0:
                    print(f" ✗ invalid size {page_w}×{page_h}")
                    continue

                # ── Simple case: page fits in viewport ─────────────────────
                if page_h <= vp_h + 10:
                    raw = page_el.screenshot(type="jpeg", quality=95)
                    if len(raw) < MIN_SLIDE_BYTES:
                        print(f" ✗ too small ({len(raw)}b)")
                        continue
                    h = img_hash(raw)
                    if h in seen_hashes:
                        print(f" ⟳ duplicate")
                        continue
                    seen_hashes.add(h)
                    page_images[page_num] = raw
                    print(f"  ✓ {len(raw)//1024}KB")

                else:
                    # ── Strip-stitch: page taller than viewport ─────────────
                    # Same algorithm as the extension:
                    # scroll in strips, capture each strip, stitch in PIL
                    from PIL import Image as PILImage
                    import io

                    print(f" (tall {page_h:.0f}px > vp {vp_h}px) ", end="", flush=True)

                    strips = []
                    captured_h = 0
                    scroll_container = pg.evaluate("""
                        (el) => {
                            let node = el.parentElement;
                            while (node && node !== document.documentElement) {
                                const ov = getComputedStyle(node).overflow + getComputedStyle(node).overflowY;
                                if (/(hidden|scroll|auto)/.test(ov)) return true;
                                node = node.parentElement;
                            }
                            return false;
                        }
                    """, page_el)

                    while captured_h < page_h:
                        cur_bb = page_el.bounding_box()
                        if not cur_bb:
                            break

                        # How much is scrolled past (above viewport)
                        scrolled_past = max(0, -cur_bb["y"])
                        visible_top   = max(0, cur_bb["y"])
                        visible_bot   = min(vp_h, cur_bb["y"] + cur_bb["height"])
                        strip_h       = visible_bot - visible_top

                        if strip_h <= 5:
                            break

                        # Capture just this element at current scroll position
                        # We clip to the visible portion manually
                        try:
                            # Screenshot the full visible page element
                            strip_raw = page_el.screenshot(
                                type="png",
                                clip={
                                    "x": cur_bb["x"],
                                    "y": visible_top,
                                    "width": page_w,
                                    "height": strip_h,
                                }
                            )
                            strips.append((scrolled_past, strip_h, strip_raw))
                        except Exception as e:
                            print(f"strip err: {e}", end=" ")

                        # Update captured_h from real DOM position (no float drift)
                        captured_h = scrolled_past + strip_h

                        # Scroll to next strip if more to capture
                        if captured_h < page_h:
                            safe_eval(pg,
                                f"document.scrollingElement.scrollTop += {int(strip_h)}")
                            time.sleep(STRIP_SETTLE)

                    # Stitch all strips into one image
                    if strips:
                        dpr = 2  # device_scale_factor
                        full_w = int(page_w * dpr)
                        full_h = int(page_h * dpr)
                        full = PILImage.new("RGB", (full_w, full_h), (255, 255, 255))

                        for (sp, sh, raw) in strips:
                            strip_img = PILImage.open(io.BytesIO(raw))
                            dst_y = int(sp * dpr)
                            full.paste(strip_img, (0, dst_y))

                        buf = io.BytesIO()
                        full.save(buf, format="JPEG", quality=95)
                        stitched = buf.getvalue()

                        h = img_hash(stitched)
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            page_images[page_num] = stitched
                            print(f"stitched {len(stitched)//1024}KB from {len(strips)} strips")
                        else:
                            print("duplicate after stitch")

                # Scroll back to page top for next page
                pg.evaluate(
                    "(el) => el.scrollIntoView({behavior:'instant', block:'start'})",
                    page_el
                )
                time.sleep(0.2)

            except Exception as e:
                print(f" ✗ {e}")
                continue

        print(f"\n  ✓ Captured {len(page_images)}/{total} pages")
        browser.close()

    return None, title, {
        "page_screenshots": page_images,
        "jsonp_urls":       [],
        "total_pages":      len(page_images),
    }


# ─── PDF BUILDER ──────────────────────────────────────────────────────────────
def build_pdf(page_screenshots, title):
    import fitz
    from PIL import Image as PILImage
    import io

    ensure_dirs()
    total = len(page_screenshots)
    if not total:
        print("✗ No pages to build PDF from.")
        return None

    print(f"\n🔨 Building PDF ({total} pages)…")
    doc = fitz.open()

    for pn in sorted(page_screenshots):
        img_bytes = page_screenshots[pn]
        try:
            pil = PILImage.open(io.BytesIO(img_bytes))
            w_px, h_px = pil.size
        except:
            w_px, h_px = 1280, 960

        img_path = IMAGES_DIR / f"p{pn:04d}.jpg"
        img_path.write_bytes(img_bytes)

        # Match physical size at 96dpi (same as screen)
        dpi  = 96
        w_pt = w_px * 72 / dpi
        h_pt = h_px * 72 / dpi
        if w_pt > 1200:
            scale = 1200 / w_pt
            w_pt *= scale; h_pt *= scale

        pg = doc.new_page(width=w_pt, height=h_pt)
        pg.insert_image(fitz.Rect(0, 0, w_pt, h_pt), filename=str(img_path))
        print(f"  ✓ p{pn}/{total}  {w_px}×{h_px}px")

    pdf_path = OUTPUT_DIR / f"{title}.pdf"
    if pdf_path.exists():
        try: pdf_path.unlink()
        except Exception as e: print(f"  ⚠ Cannot delete existing PDF: {e}")

    doc.save(str(pdf_path), garbage=4, deflate=True, clean=True)
    doc.close()

    mb = pdf_path.stat().st_size / 1024 / 1024
    print(f"\n✅ PDF → {pdf_path}")
    print(f"   Pages : {total}")
    print(f"   Size  : {mb:.2f} MB")
    return str(pdf_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────
def get_args():
    p = argparse.ArgumentParser(
        description="Scribd Downloader PRO — Element + Strip-Stitch Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("url", help="Any Scribd document URL")
    p.add_argument("--cookies", default=None,
                   help="Path to cookies.json (Cookie-Editor → Export All)")
    p.add_argument("--images-only", action="store_true",
                   help="Skip PDF build, keep only JPEG images")
    return p.parse_args()


def main():
    args    = get_args()
    cookies = []

    if args.cookies and os.path.exists(args.cookies):
        cookies = load_cookies_file(args.cookies)
        print(f"🍪 Loaded {len(cookies)} cookies from {args.cookies}")
    elif SCRIBD_COOKIE_STRING:
        cookies = parse_cookie_string(SCRIBD_COOKIE_STRING)
    else:
        print("⚠  No cookies — only public documents will load fully.\n"
              "   Cookie-Editor → Export All → cookies.json\n"
              "   Then: --cookies cookies.json\n")

    _, title, data = scrape_scribd(args.url, cookies, args.images_only)

    shots = data.get("page_screenshots", {})
    if not shots:
        print("✗ No pages captured.")
        sys.exit(1)

    if not args.images_only:
        build_pdf(shots, title)
    else:
        ensure_dirs()
        for pn, raw in sorted(shots.items()):
            p = IMAGES_DIR / f"p{pn:04d}.jpg"
            p.write_bytes(raw)
        print(f"✅ {len(shots)} images saved → {IMAGES_DIR}")

    print("\n🎉 Done!")


if __name__ == "__main__":
    main()
