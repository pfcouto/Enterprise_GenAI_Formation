#!/usr/bin/env python3
"""
Syone website scraper (Stage 1a of the formation pipeline).

Crawls https://www.syone.com through its public sitemap.xml (robots.txt allows it) and writes
one clean Markdown file per page into data/raw_syone_corp/, plus the content images into
data/extracted_images/syone_corp/ and a manifest (_manifest.json) describing exactly what was scraped.

Design rules (read these before changing anything):
  * NO silent fallback. If a page cannot be fetched it is reported as FAILED in the manifest and the
    script exits non-zero when nothing could be scraped. A fresh clone ships a dated snapshot of a
    successful run, so a formation can still run offline; re-running this script refreshes it.
  * Only English pages are scraped (the /pt/ mirror is skipped) so the knowledge base is not duplicated.
  * Q&A is preserved: accordion FAQ blocks become `### question` + answer under a `## Frequently asked questions`.
  * Images: logos, certification badges, sitewide chrome, tracking pixels and CTA banners are dropped.
    Only images that sit in the page body are kept (max --max-images-per-page per page).

Usage:
  python scripts/scrape_syone.py                      # core profile (~60 pages, every non-blog page + 30 articles)
  python scripts/scrape_syone.py --profile full       # every English page in the sitemap (~250 pages)
  python scripts/scrape_syone.py --max-blog 60        # more blog articles
  python scripts/scrape_syone.py --no-images          # text only
"""

import argparse
import collections
import datetime as dt
import difflib
import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote, parse_qs

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image

BASE = "https://www.syone.com"
SITEMAP = f"{BASE}/sitemap.xml"
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw_syone_corp"
IMAGES_DIR = ROOT / "data" / "extracted_images" / "syone_corp"
CURATED_FILE = Path(__file__).parent / "dataset_builder" / "syone_images_curated.json"
USER_AGENT = "SyoneFormationBot/1.0 (+training exercise; polite crawler, 1 request / 0.6 s)"

# URL sections that carry the company knowledge we want. Order = priority.
CORE_SECTIONS = ["", "about", "about-syone", "what-we-do", "how-we-do-it", "technologies", "partners",
                 "ezsearch-syone", "careers", "contact-us", "social-responsibility-at-syone",
                 "red-hat", "suse", "camunda", "microsoft", "news", "content-hub"]
SKIP_PREFIXES = ("pt", "event", "events", "media")  # PT mirror + historic event/media archives (enable with --profile full)
INDEX_PAGES = {"blog", "news", "content-hub"}
MIN_WORDS = 60
KEEP_SHORT = {"contact-us", "careers"}
SKIP_HEADINGS = {"recent articles", "related articles", "related posts", "share this article", "subscribe",
                 "our certifications", "see all", "in this article", "table of contents"}
STOP_HEADINGS = {"recent articles", "related articles", "related posts"}
LOGO_HINT = re.compile(r"logo|iso[_ -]?\d|badge|favicon|icon|certif|partners? portugal|sprite|pixel|spacer|gns|nato", re.I)
CTA_HOSTS = ("hubspot-no-cache", "hubspotusercontent")


# ----------------------------------------------------------------------------------------------
# Sitemap
# ----------------------------------------------------------------------------------------------
def fetch_sitemap(client: httpx.Client):
    resp = client.get(SITEMAP)
    resp.raise_for_status()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(resp.text)
    items = []
    for u in root.findall("s:url", ns):
        loc = u.findtext("s:loc", namespaces=ns)
        last = u.findtext("s:lastmod", namespaces=ns) or ""
        if loc:
            items.append((loc.strip(), last))
    return items


def section_of(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.split("/")[0] if path else ""


def select_pages(items, profile: str, max_blog: int):
    """Returns the list of (url, lastmod) to scrape for the chosen profile."""
    seen, selected, blog = set(), [], []
    for url, last in items:
        url = url.rstrip("/")
        if url in seen:
            continue
        seen.add(url)
        sec = section_of(url)
        if sec in SKIP_PREFIXES and profile != "full":
            continue
        if sec == "pt" or "sample-" in url:
            continue
        if sec == "blog":
            blog.append((url, last))
        elif profile == "full" or sec in CORE_SECTIONS or url.count("/") <= 3:
            selected.append((url, last))
    blog.sort(key=lambda x: x[1], reverse=True)  # most recent first
    selected.extend(blog if profile == "full" else blog[:max_blog])
    return selected


# ----------------------------------------------------------------------------------------------
# HTML -> Markdown
# ----------------------------------------------------------------------------------------------
def clean(text: str) -> str:
    text = text.replace(" ", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def inline_text(el: Tag) -> str:
    """Text of an element with inline links rendered as [text](url) when they point to syone pages."""
    parts = []
    for node in el.descendants:
        if isinstance(node, NavigableString):
            if node.parent and node.parent.name in ("script", "style"):
                continue
            parts.append(str(node))
    return clean(" ".join(parts))


def strip_accordion_marker(text: str) -> str:
    return re.sub(r"\s*\+\s*$", "", text).strip()


def element_to_blocks(main: Tag):
    """Walks the page body in document order and yields (kind, text) blocks."""
    for bad in main.select("script, style, noscript, nav, footer, header, form, svg, iframe, .hs-form, "
                           ".cookie, #hs-eu-cookie-confirmation, .hs_cos_wrapper_type_form, button"):
        bad.decompose()

    blocks, skipping, in_faq = [], False, False
    BLOCKISH = ["div", "section", "p", "li", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"]
    for el in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table", "blockquote", "div", "span"]):
        if el.name in ("div", "span"):
            # Leaf containers only (e.g. flip-card text, address blocks); skip if text lives inside a real block.
            if el.find(BLOCKISH) or el.find_parent(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "a", "table", "label"]):
                continue
            if el.name == "span" and el.parent and el.parent.name not in ("div", "section"):
                continue
            if len(inline_text(el)) < 25:
                continue
        if el.name == "li" and el.find(["p", "ul", "ol"]):
            continue  # container li: its children are emitted on their own
        if el.name != "table" and el.find_parent("table"):
            continue
        if el.name == "p" and el.find_parent("li"):
            continue
        if el.name == "li" and el.find_parent("li"):
            pass
        if el.name == "a":
            continue
        text = inline_text(el)
        if not text:
            continue
        low = strip_accordion_marker(text).lower()

        if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = "h4" if el.name in ("h5", "h6") else el.name
            if low in STOP_HEADINGS:
                break
            skipping = low in SKIP_HEADINGS
            if skipping:
                continue
            is_accordion = "accordion-header" in (el.get("class") or [])
            if "frequently asked" in low or low == "faq":
                in_faq = True
                blocks.append(("h2", "Frequently asked questions"))
                continue
            if is_accordion:
                blocks.append(("h3", strip_accordion_marker(text)))
                continue
            if el.name == "h2" and not is_accordion:
                in_faq = in_faq and False
            blocks.append((level, strip_accordion_marker(text)))
            continue
        if skipping:
            continue
        if el.find_parent(class_=re.compile(r"\bbtn\b")) or (el.name == "p" and len(text) < 3):
            continue
        if el.name == "table":
            rows = []
            for tr in el.find_all("tr"):
                cells = [clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append(("table", rows))
        elif el.name == "li":
            blocks.append(("li", text))
        elif el.name == "blockquote":
            blocks.append(("quote", text))
        else:
            blocks.append(("p", text))
    return prune_blocks(blocks)


def prune_blocks(blocks):
    """Drops repeated text and headings that introduce nothing (followed by an equal/higher heading or the end)."""
    deduped = []
    for b in blocks:
        if deduped and deduped[-1] == b:
            continue
        deduped.append(b)
    rank = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}
    pruned = []
    for i, (kind, val) in enumerate(deduped):
        if kind in rank:
            nxt = deduped[i + 1] if i + 1 < len(deduped) else None
            if nxt is None or (nxt[0] in rank and (rank[nxt[0]] <= rank[kind] or nxt[1] == val)):
                continue
        pruned.append((kind, val))
    return pruned


def blocks_to_markdown(blocks, title: str) -> str:
    out, last_h1 = [], None
    prev = None
    for kind, val in blocks:
        if kind == "h1":
            if clean(val).lower() == clean(title).lower() and last_h1 is None:
                last_h1 = val
                continue
            out.append(f"\n## {val}\n")
        elif kind == "h2":
            out.append(f"\n## {val}\n")
        elif kind == "h3":
            out.append(f"\n### {val}\n")
        elif kind == "h4":
            out.append(f"\n#### {val}\n")
        elif kind == "li":
            out.append(f"- {val}")
        elif kind == "quote":
            out.append(f"\n> {val}\n")
        elif kind == "table":
            width = max(len(r) for r in val)
            rows = [r + [""] * (width - len(r)) for r in val]
            out.append("")
            out.append("| " + " | ".join(rows[0]) + " |")
            out.append("|" + "---|" * width)
            for r in rows[1:]:
                out.append("| " + " | ".join(r) + " |")
            out.append("")
        else:
            if prev == "li":
                out.append("")
            out.append(val + "\n")
        prev = kind
    md = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


# ----------------------------------------------------------------------------------------------
# Images
# ----------------------------------------------------------------------------------------------
def image_dimensions_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    w = int(q["width"][0]) if "width" in q else (int(q["length"][0]) if "length" in q else None)
    h = int(q["height"][0]) if "height" in q else None
    return w, h


def candidate_images(main: Tag, page_url: str):
    seen, found = set(), []
    for img in main.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        src = urljoin(page_url, src)
        host = urlparse(src).netloc
        if any(h in host for h in CTA_HOSTS):
            continue
        base_key = src.split("?")[0]
        if base_key in seen:
            continue
        seen.add(base_key)
        alt = clean(img.get("alt", ""))
        w, h = image_dimensions_from_url(src)
        found.append({"src": src, "base": base_key, "alt": alt, "width": w, "height": h})
    return found


def is_content_image(c: dict, sitewide: set) -> bool:
    if c["base"] in sitewide:
        return False
    name = unquote(Path(urlparse(c["src"]).path).name)
    if LOGO_HINT.search(name) or LOGO_HINT.search(c["alt"]):
        return False
    if c["width"] is not None and c["width"] < 300:
        return False
    return True


def download_image(client: httpx.Client, c: dict, slug: str, idx: int):
    # slug is the file stem; the same figure used on several pages is downloaded once (see saved_by_base)
    """Downloads, converts to PNG/JPG (first frame for gifs) and returns saved Path or None."""
    try:
        resp = client.get(c["src"])
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        img.seek(0)
        if img.width < 300 or img.height < 120:
            return None
        if img.width > 1400:
            img = img.resize((1400, int(img.height * 1400 / img.width)))
        if img.mode in ("RGBA", "P", "LA"):  # flatten transparency on white (maps/diagrams would turn black otherwise)
            rgba = img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, "white")
            bg.alpha_composite(rgba)
            img, ext = bg.convert("RGB"), "png"
        else:
            img, ext = img.convert("RGB"), "jpg"
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        path = IMAGES_DIR / (f"{slug}-{idx}.{ext}" if idx != "" else f"{slug}.{ext}")
        img.save(path)
        return path
    except Exception as e:  # noqa: BLE001 - one broken image must not kill the crawl
        print(f"      image skipped ({c['src'][:70]}...): {e}")
        return None


# ----------------------------------------------------------------------------------------------
# Crawl
# ----------------------------------------------------------------------------------------------
def slug_for(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "home"
    return re.sub(r"[^a-z0-9\-]+", "-", path.lower().replace("/", "_")).strip("-")[:110]


def parse_page(html: str, url: str):
    soup = BeautifulSoup(html, "html.parser")
    title = clean(soup.title.get_text()) if soup.title else ""
    h1 = soup.find("h1")
    page_title = clean(h1.get_text(" ")) if h1 else title
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = clean(desc_tag["content"]) if desc_tag and desc_tag.get("content") else ""
    pub = soup.find("meta", attrs={"property": "article:published_time"})
    main = soup.find("main") or soup.body
    return soup, title, page_title, description, (pub["content"] if pub and pub.get("content") else ""), main


def main():
    ap = argparse.ArgumentParser(description="Scrape syone.com into data/raw_syone_corp/")
    ap.add_argument("--profile", choices=["core", "full"], default="core")
    ap.add_argument("--max-blog", type=int, default=30, help="blog articles to include in the core profile")
    ap.add_argument("--max-images-per-page", type=int, default=3)
    ap.add_argument("--delay", type=float, default=0.6, help="seconds between requests (be polite)")
    ap.add_argument("--images", choices=["curated", "heuristic", "none"], default="curated",
                    help="curated: keep only images hand-reviewed as informative (scripts/dataset_builder/syone_images_curated.json); "
                         "heuristic: keep every non-logo body image; none: text only")
    ap.add_argument("--no-images", action="store_true", help="alias for --images none")
    args = ap.parse_args()
    if args.no_images:
        args.images = "none"
    curated = {}
    if args.images == "curated" and CURATED_FILE.exists():
        curated = json.loads(CURATED_FILE.read_text(encoding="utf-8"))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc)
    client = httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": USER_AGENT})

    print("=" * 78)
    print("Syone website scraper - live crawl of https://www.syone.com")
    print("=" * 78)
    try:
        items = fetch_sitemap(client)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"ERROR: could not read {SITEMAP}: {e}\n"
                 "Offline? A dated snapshot of a previous successful run is committed in data/raw_syone_corp/.")
    pages = select_pages(items, args.profile, args.max_blog)
    print(f"Sitemap: {len(items)} URLs; profile '{args.profile}' selects {len(pages)} pages\n")

    # Pass 1: fetch + parse everything (images are decided after we know which images are sitewide chrome)
    fetched = []
    for n, (url, lastmod) in enumerate(pages, 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            if "text/html" not in resp.headers.get("content-type", ""):
                raise ValueError("not HTML")
            soup, title, page_title, desc, published, main_el = parse_page(resp.text, url)
            imgs = candidate_images(main_el, str(resp.url))
            blocks = element_to_blocks(main_el)
            fetched.append({"url": url, "lastmod": lastmod, "title": page_title or title, "html_title": title,
                            "description": desc, "published": published, "blocks": blocks, "images": imgs})
            words = sum(len(str(b[1]).split()) for b in blocks)
            print(f"[{n:3}/{len(pages)}] ok   {words:5} words  {url.replace(BASE, '') or '/'}")
        except Exception as e:  # noqa: BLE001
            fetched.append({"url": url, "error": str(e)})
            print(f"[{n:3}/{len(pages)}] FAIL {url} ({e})")
        time.sleep(args.delay)

    ok_pages = [p for p in fetched if "error" not in p]
    if not ok_pages:
        sys.exit("ERROR: no page could be scraped. Check your connection; a committed snapshot is still available.")

    # Images that appear on >= 4 pages are site chrome (client logo bar, ISO badges, CTA banners...)
    counter = collections.Counter(i["base"] for p in ok_pages for i in p["images"])
    sitewide = {b for b, c in counter.items() if c >= 4}

    # Pass 2: write markdown + download content images
    for old in RAW_DIR.glob("*.md"):
        old.unlink()
    if args.images != "none" and IMAGES_DIR.exists():
        for old in list(IMAGES_DIR.glob("*.png")) + list(IMAGES_DIR.glob("*.jpg")):
            old.unlink()

    manifest, total_images, kept_bodies = []
    saved_by_base: dict = {}, 0, []
    for p in fetched:
        if "error" in p:
            manifest.append({"url": p["url"], "status": "failed", "error": p["error"]})
            continue
        body_text = " ".join(str(b[1]) for b in p["blocks"] if b[0] != "table")
        slug_guess = slug_for(p["url"])
        if slug_guess in INDEX_PAGES or (len(body_text.split()) < MIN_WORDS and slug_guess not in KEEP_SHORT):
            manifest.append({"url": p["url"], "status": "skipped", "reason": "index/too short"})
            continue
        if any(difflib.SequenceMatcher(None, body_text[:2500], other[:2500]).quick_ratio() > 0.97
               and difflib.SequenceMatcher(None, body_text[:2500], other[:2500]).ratio() > 0.9 for other in kept_bodies):
            manifest.append({"url": p["url"], "status": "skipped", "reason": "near-duplicate of another page"})
            continue
        kept_bodies.append(body_text)
        slug = slug_for(p["url"])
        saved_images = []
        if args.images != "none":
            if args.images == "curated":
                keep = [c for c in p["images"] if c["base"] in curated]
                for c in keep:
                    c["alt"] = curated[c["base"]]["caption"]
                    c["description"] = curated[c["base"]].get("description", "")
            else:
                keep = [c for c in p["images"] if is_content_image(c, sitewide)][: args.max_images_per_page]
            for i, c in enumerate(keep, 1):
                if c["base"] in saved_by_base:          # same figure on another page: reuse the one file
                    path = saved_by_base[c["base"]]
                else:
                    stem = curated.get(c["base"], {}).get("file")
                    path = download_image(client, c, stem, "") if stem else download_image(client, c, slug, i)
                    if path:
                        saved_by_base[c["base"]] = path
                if path:
                    saved_images.append({"file": path.name, "alt": c["alt"], "description": c.get("description", ""), "source_url": c["src"]})
                    time.sleep(0.2)
        total_images += len(saved_images)

        body = blocks_to_markdown(p["blocks"], p["title"])
        section = section_of(p["url"]) or "home"
        header = [f"# {p['title']}", "", f"Source: {p['url']}", f"Section: {section}"]
        if p["published"]:
            header.append(f"Published: {p['published'][:10]}")
        if p["description"]:
            header.append(f"Summary: {p['description']}")
        header.append(f"Scraped: {started.date().isoformat()}")
        md = "\n".join(header) + "\n\n" + body + "\n"
        if saved_images:
            md += "\n## Images on this page\n\n"
            for im in saved_images:
                alt = im["alt"] or Path(im["file"]).stem.replace("-", " ")
                md += f"![{alt}](/static/images/syone_corp/{im['file']})\n\n"
                if im.get("description"):
                    md += f"> Figure description: {im['description']}\n\n"
        (RAW_DIR / f"{slug}.md").write_text(md, encoding="utf-8")
        manifest.append({"url": p["url"], "slug": slug, "section": section, "title": p["title"], "status": "ok",
                         "words": len(body.split()), "images": saved_images,
                         "has_faq": "Frequently asked questions" in body})

    ok = [m for m in manifest if m["status"] == "ok"]
    skipped = [m for m in manifest if m["status"] == "skipped"]
    (RAW_DIR / "_manifest.json").write_text(json.dumps({
        "scraped_at": started.isoformat(), "profile": args.profile, "source": SITEMAP,
        "pages_ok": len(ok), "pages_failed": len(manifest) - len(ok) - len(skipped), "pages_skipped": len(skipped), "images": total_images,
        "sitewide_images_dropped": len(sitewide), "pages": manifest}, indent=2), encoding="utf-8")

    by_sec = collections.Counter(m["section"] for m in ok)
    print("\n" + "=" * 78)
    print(f"Done: {len(ok)} pages kept ({len(skipped)} skipped as index/duplicate), {len(manifest) - len(ok) - len(skipped)} failed, {total_images} content images kept "
          f"({len(sitewide)} sitewide images dropped)")
    print("Pages per section:", dict(by_sec))
    print(f"Markdown: {RAW_DIR}\nImages:   {IMAGES_DIR}\nManifest: {RAW_DIR / '_manifest.json'}")
    print("=" * 78)
    if len(manifest) - len(ok) - len(skipped) > len(manifest) // 3:
        sys.exit("ERROR: more than a third of the pages failed.")


if __name__ == "__main__":
    main()
