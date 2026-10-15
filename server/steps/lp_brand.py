"""Option 2 helpers: read a client's existing website for its branding (logo,
colours, fonts), its photos, and its privacy/terms text. Network + HTML only,
no Claude calls (the caller asks Claude to pick design tokens from the digest)."""

import html
import re
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser

UA = {"User-Agent": "Mozilla/5.0 (compatible; LFTCampaignBuilder/1.0)"}


def fetch(url, binary=False, limit=3_000_000):
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"Not a web link: {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read(limit)
        ctype = r.headers.get("Content-Type", "")
    return (data, ctype) if binary else data.decode("utf-8", "replace")


def _absolute(base, href):
    return urllib.parse.urljoin(base, href.strip()) if href else ""


def _hex6(h):
    h = h.lower().lstrip("#")
    return "#" + (h if len(h) == 6 else "".join(c * 2 for c in h))


def _is_colourful(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) > 28 and 25 < (r + g + b) / 3 < 235


_NOT_GOOGLE = re.compile(r"helvetica|din-next|madefor|arial|sans-serif|serif|system-ui|inherit|^-", re.I)


def clean_font(name):
    """CSS family -> Google Fonts family. Wix writes 'open-sans-v2', 'montserrat',
    'roboto-slab-w01-regular'; strip the platform suffixes and title-case."""
    n = name.strip().strip("'\"")
    if not n or _NOT_GOOGLE.search(n):
        return ""
    n = re.sub(r"[-_ ]?(?:v\d+|w\d{2}.*|regular|bold|light|medium|semibold|italic)$", "", n, flags=re.I)
    n = re.sub(r"[-_]+", " ", n).strip()
    return n.title() if n.islower() else n


def digest(home_url):
    """Everything Claude needs to pick this site's design tokens + the raw
    candidates for logo / photos / legal pages."""
    home = fetch(home_url)
    css = re.findall(r"<style[^>]*>(.*?)</style>", home, re.S | re.I)
    sheets = [re.search(r'href=["\']([^"\']+)', t, re.I) for t in re.findall(r"<link\b[^>]*>", home, re.I)
              if re.search(r'rel=["\']stylesheet["\']', t, re.I)]
    for m in sheets[:6]:
        href = html.unescape(m.group(1)) if m else ""
        if not href or "fonts.googleapis" in href:
            continue
        try:
            css.append(fetch(_absolute(home_url, href), limit=400_000))
        except Exception:  # noqa: BLE001 - a missing stylesheet shouldn't stop the build
            pass
    css_text = "\n".join(css)
    counts = Counter(_hex6(h) for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", css_text + home))
    colours = [c for c, _ in counts.most_common(40) if _is_colourful(c)][:8]
    named = re.findall(r"--[\w-]*(?:primary|accent|brand|main|cta|button)[\w-]*\s*:\s*(#[0-9a-fA-F]{3,6})", css_text, re.I)
    theme = re.findall(r'name=["\']theme-color["\'][^>]*content=["\']([^"\']+)', home, re.I)
    all_css = css_text + "\n" + "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", home, re.S | re.I))
    fonts = Counter(clean_font(f) for decl in re.findall(r"font-family\s*:\s*([^;}{]+)", all_css, re.I)
                    for f in decl.split(",")[:1])
    fonts.pop("", None)
    heading = ""
    for m in re.finditer(r"(?:^|[},\s])(h[1-3])\s*(?:,\s*h[1-6]\s*)*\{[^{}]*?font-family\s*:\s*([^;}]+)", all_css, re.I):
        heading = clean_font(m.group(2).split(",")[0])
        if heading:
            break
    google = [html.unescape(g) for g in re.findall(r'href=["\'](https://fonts\.googleapis\.com/css[^"\']+)', home, re.I)]

    logos = []
    for tag in re.findall(r"<img\b[^>]*>", home, re.I):
        src = re.search(r'\bsrc=["\']([^"\']+)', tag, re.I)
        if src and re.search(r"logo", tag, re.I):
            logos.append(_absolute(home_url, src.group(1)))
    for m in re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', home, re.I):
        logos.append(_absolute(home_url, m))

    # favicon candidates, best first (apple-touch-icon is the largest, then sized icons, then /favicon.ico)
    icons = []
    for tag in re.findall(r"<link\b[^>]*>", home, re.I):
        rel = re.search(r'rel=["\']([^"\']+)', tag, re.I)
        href = re.search(r'href=["\']([^"\']+)', tag, re.I)
        if rel and href and "icon" in rel.group(1).lower() and "mask" not in rel.group(1).lower():
            size = re.search(r'sizes=["\'](\d+)', tag, re.I)
            icons.append((-(int(size.group(1)) if size else 0) - (1000 if "apple" in rel.group(1).lower() else 0),
                          _absolute(home_url, html.unescape(href.group(1)))))
    icons = [u for _, u in sorted(icons, key=lambda t: t[0])]
    icons.append(_absolute(home_url, "/favicon.ico"))

    images = []
    for src in re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)", home, re.I):
        u = _absolute(home_url, src)
        if re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I) and not re.search(r"logo|icon|sprite|avatar", u, re.I):
            images.append(u)
    return {
        "home_html": home, "title": (re.search(r"<title[^>]*>(.*?)</title>", home, re.S | re.I) or [0, ""])[1].strip(),
        "colours": colours, "named_colours": named, "theme_color": theme[:1],
        "fonts": [f for f, _ in fonts.most_common(6)], "heading_font": heading, "google_fonts": google[:2],
        "logo_candidates": list(dict.fromkeys(logos))[:6], "favicon_candidates": list(dict.fromkeys(icons))[:6], "images": list(dict.fromkeys(images))[:40],
    }


def google_fonts_url(head, body):
    fam = lambda n, w: "family=" + urllib.parse.quote_plus(n) + ":wght@" + w
    if head == body:
        return "https://fonts.googleapis.com/css2?" + fam(head, "400;600;700;800") + "&display=swap"
    return ("https://fonts.googleapis.com/css2?" + fam(head, "700;800") + "&" + fam(body, "400;600;700")
            + "&display=swap")


# ---------- privacy / terms copied from the client's own site ----------

SKIP = {"script", "style", "nav", "header", "footer", "form", "svg", "noscript", "iframe", "button", "select"}
KEEP = {"h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "b", "em", "i", "br", "a", "table", "thead", "tbody",
        "tr", "th", "td"}


class _Clean(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.out, self.skip, self.in_h1 = base, [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag == "h1":
            self.in_h1 += 1  # the page writes its own H1
        elif tag in KEEP and not self.skip and not self.in_h1:
            href = dict(attrs).get("href", "")
            if tag == "a":
                href = _absolute(self.base, href)
                if not re.match(r"(https?:|mailto:|tel:)", href):
                    self.out.append("<a>")
                    return
                self.out.append(f'<a href="{href}" rel="noopener">')
            else:
                self.out.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "h1":
            self.in_h1 = max(0, self.in_h1 - 1)
        elif tag in KEEP and tag != "br" and not self.skip and not self.in_h1:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip and not self.in_h1:
            self.out.append(data.replace("&", "&amp;").replace("<", "&lt;"))


def extract_legal_body(page_html, base):
    m = (re.search(r"<main\b[^>]*>(.*)</main>", page_html, re.S | re.I)
         or re.search(r"<article\b[^>]*>(.*)</article>", page_html, re.S | re.I)
         or re.search(r"<body\b[^>]*>(.*)</body>", page_html, re.S | re.I))
    p = _Clean(base)
    inner = m.group(1) if m else page_html
    title = re.search(r"<h[12]\b[^>]*>[^<]*(?:privacy|terms|policy|conditions)", inner, re.I)
    h1 = title or re.search(r"<h1\b", inner, re.I)
    p.feed(inner[h1.start():] if h1 else inner)  # start at the page title, skipping any nav above it
    body = "".join(p.out)
    body = re.sub(r"<a(?: [^>]*)?>\s*</a>", "", body)
    body = re.sub(r"<a [^>]*>\s*(?:tap to call|get (?:a )?free quote|free quote|call now|call us)[^<]*(?:<strong>[^<]*</strong>)?\s*</a>",
                  "", body, flags=re.I)
    body = re.sub(r"^\s*<h[2-4]>[^<]*(?:privacy|terms|policy|conditions)[^<]*</h[2-4]>", "", body, flags=re.I)
    body = re.sub(r"<(p|li|h[2-4])>\s*</\1>", "", body)
    body = re.sub(r"\n\s*\n+", "\n", body).strip()
    return body if len(re.sub(r"<[^>]+>", "", body).split()) > 80 else ""


def find_legal(home_html, home_url):
    """{"privacy": url|None, "terms": url|None} from the home page's links."""
    found = {"privacy": None, "terms": None}
    for href, text in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', home_html, re.S | re.I):
        label = re.sub(r"<[^>]+>", "", text).lower() + " " + href.lower()
        if not found["privacy"] and "privacy" in label:
            found["privacy"] = _absolute(home_url, href)
        elif not found["terms"] and re.search(r"terms|conditions", label):
            found["terms"] = _absolute(home_url, href)
    return found
