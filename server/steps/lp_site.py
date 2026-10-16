"""Turns the template's landing page master (content/lp-master.html in the
site-template repo) into one client's pages. No Claude calls here: callers pass
in the copy; this file only places it, resizes photos and checks that nothing
from the template's own client (Bolt Concreting) is left behind."""

import html
import io
import os
import re

from PIL import Image

E = lambda s: html.escape(str(s), quote=True)  # noqa: E731
DASHES = re.compile(r"\s*[—–]\s*")
STAR = '<svg class="i"><use href="#i-star"/></svg>'
ICONS = {"doc", "user", "rain", "shield", "clock", "hammer", "truck", "pin"}
# Strings from the template's own client; none may survive into another client's page.
LEAKS = ("Bolt", "Palmerston", "palmerstonnorthconcreting", "Manawat", "Palmy", "027 909", "TQK5ZDP3",
         "Ashhurst", "Feilding", "Rose W.")


def no_dashes(s):
    return DASHES.sub(", ", s)


# ---------- photos ----------

def load_image(path_or_bytes):
    im = Image.open(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes)
    im.load()
    return im.convert("RGB")


def save_sizes(im, out_dir, stem, widths):
    """Write <stem>-<w>.webp for each width (never upscaled). Returns {w: (w, h)}."""
    os.makedirs(out_dir, exist_ok=True)
    sizes = {}
    for w in widths:
        w2 = min(w, im.width)
        h2 = round(im.height * w2 / im.width)
        im.resize((w2, h2), Image.LANCZOS).save(os.path.join(out_dir, f"{stem}-{w}.webp"), "WEBP", quality=80)
        sizes[w] = (w2, h2)
    return sizes


def jpeg_thumb(im, width=512):
    t = im.copy()
    t.thumbnail((width, width))
    buf = io.BytesIO()
    t.save(buf, "JPEG", quality=70)
    return buf.getvalue()


def write_icons(logo_im, img_dir, site_dir, bare=False):
    """Favicon set. bare=True: logo_im is the client's real favicon, fill the
    square with it. Otherwise centre the logo on a white square."""
    def square(n):
        c = Image.new("RGBA", (n, n), (255, 255, 255, 255))
        l = logo_im.convert("RGBA")
        l.thumbnail((n, n) if bare else (int(n * .86), int(n * .86)), Image.LANCZOS)
        c.paste(l, ((n - l.width) // 2, (n - l.height) // 2), l)
        return c.convert("RGB")
    os.makedirs(img_dir, exist_ok=True)
    square(32).save(os.path.join(img_dir, "favicon.png"))
    square(32).save(os.path.join(img_dir, "favicon-dark.png"))
    square(192).save(os.path.join(img_dir, "webclip-192.png"))
    square(180).save(os.path.join(site_dir, "apple-touch-icon.png"))
    square(48).save(os.path.join(site_dir, "favicon.ico"), sizes=[(48, 48)])


# ---------- master -> client master ----------

def _between(p, start, end, new):
    i = p.index(start)
    j = p.index(end, i)
    return p[:i] + new + p[j:]


def _stars(n=5):
    return STAR * n


def work_section(d, order=None):
    """Our-work gallery. order = photo indexes best-first for this page."""
    photos = d["photos"]
    idx = [i for i in (order or []) if 0 <= i < len(photos)]
    idx += [i for i in range(len(photos)) if i not in idx]
    btns = []
    for n, i in enumerate(idx):
        ph = photos[i]
        more = ' class="more" hidden' if n >= 12 else ""
        btns.append(
            f'      <button type="button"{more} data-full="img/work-{i}-900.webp"><img src="img/work-{i}-480.webp" '
            f'alt="{E(ph["alt"])}" loading="lazy" width="{ph["w"]}" height="{ph["h"]}"><span>{E(ph["label"])}</span></button>')
    # The page's script always looks up #more-work, so the button must exist.
    hide = "" if len(idx) > 12 else " hidden"
    more_btn = f'    <button type="button" class="btn btn-ink btn-more" id="more-work"{hide}>Show all {len(idx)} photos</button>\n'
    w = d["work"]
    return f'''<!-- 5. OUR WORK -->
<section class="sec" id="work">
  <div class="wrap">
    <div class="sec-head">
      <span class="eyebrow">Our work</span>
      <h2>{E(w["heading"])}</h2>
      <p>{E(w["intro"])}</p>
    </div>
    <div class="work">
{chr(10).join(btns)}
    </div>
{more_btn}    <div class="work-foot">
      <p>Want something like this at your place?</p>
      <a href="#quote" class="btn btn-accent">Get my free quote</a>
    </div>
  </div>
</section>
<dialog class="lb" id="lb" aria-label="Photo"><img src="" alt=""><button type="button" class="lb-x" aria-label="Close photo">×</button><button type="button" class="lb-nav lb-prev" aria-label="Previous photo">‹</button><button type="button" class="lb-nav lb-next" aria-label="Next photo">›</button></dialog>

'''


def build_master(M, d):
    """d: see server/steps/step5.py (_site_data). Returns the client's master HTML
    still containing {{TITLE}} {{DESC}} {{H1}} {{SUB}} {{TICKS}} {{FAQ}} and the
    hero image placeholder, ready for per-page fill-in."""
    p = M
    name, city = d["name"], d["city"]
    ph = d["photos"]

    # --- brand tokens ---
    t = d.get("tokens") or {}
    if t:
        def setvar(var, val):
            nonlocal p
            p = re.sub(rf"(--{var}:)#[0-9A-Fa-f]{{3,6}}", rf"\g<1>{val}", p, count=1)
        for var in ("accent", "accent-dark", "ink", "steel"):
            if t.get(var.replace("-", "_")):
                setvar(var, t[var.replace("-", "_")])
        if t.get("accent"):
            h = t["accent"].lstrip("#")
            p = p.replace("rgba(242,106,27", f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}")
        if t.get("ink"):
            p = p.replace('<meta name="theme-color" content="#16181B">', f'<meta name="theme-color" content="{t["ink"]}">')
        if t.get("fonts_url"):
            p = re.sub(r'https://fonts\.googleapis\.com/css2\?[^"]+', t["fonts_url"], p, count=1)
            p = p.replace('--head:"Montserrat"', f'--head:"{t["head_font"]}"').replace('--body:"Open Sans"', f'--body:"{t["body_font"]}"')

    # --- light (white) logo: the template's white nav would hide it, so run the nav dark ---
    if d.get("logo_light"):
        p = p.replace(".nav{position:sticky;top:0;z-index:50;background:#fff;border-bottom:1px solid var(--line)}",
                      ".nav{position:sticky;top:0;z-index:50;background:var(--ink);border-bottom:1px solid var(--steel)}", 1)
        p = p.replace(".nav-links a{text-decoration:none;color:var(--ink)}", ".nav-links a{text-decoration:none;color:#fff}", 1)
        p = p.replace("color:var(--ink);text-decoration:none}\n.nav-phone svg", "color:#fff;text-decoration:none}\n.nav-phone svg", 1)

    # --- logo, name, phone, tracking ---
    p = p.replace("img/logo.png", "img/" + d["logo_file"])
    p = re.sub(r'(<img src="img/logo\.[a-z]+" alt="[^"]*" )width="\d+" height="\d+"',
               rf'\g<1>width="{d["logo_w"]}" height="{d["logo_h"]}"', p)
    p = p.replace("Bolt Concreting", E(name))
    p = p.replace("tel:+64279094888", "tel:" + d["phone_e164"]).replace("027 909 4888", E(d["phone_display"]))
    if d.get("gtm_id"):
        p = p.replace("GTM-TQK5ZDP3", d["gtm_id"])
        p = re.sub(r"<!-- Google Tag Manager \(container from[^>]*-->", "<!-- Google Tag Manager -->", p)
    else:
        p = re.sub(r"<!-- Google Tag Manager.*?</script>\n", "", p, flags=re.S)
        p = re.sub(r"<noscript><iframe src=\"https://www\.googletagmanager\.com/ns\.html[^<]*</iframe></noscript>\n?", "", p)

    # --- hero rating line + nav ---
    rating = d.get("rating_line") or ""
    p = re.sub(r'<div class="rating"><span class="stars" aria-hidden="true">.*?</span>5-star rated on Facebook</div>',
               f'<div class="rating"><span class="stars" aria-hidden="true">{_stars()}</span>{E(rating)}</div>' if rating else "",
               p, flags=re.S)
    if not d.get("reviews"):
        p = p.replace('<a href="#reviews">Reviews</a>', "")

    # --- job options + form helper text ---
    opts = "".join(f"              <option>{E(o)}</option>\n" for o in d["job_options"])
    p = re.sub(r'(<option value="" disabled selected>Choose a job type</option>\n)(?:\s*<option>[^<]*</option>\n)+',
               lambda m: m.group(1) + opts, p)
    chips = "".join(
        f'                <label class="chip"><input type="radio" name="size" value="{E(c["value"])}"><span>{E(c["label"])}'
        f'<small>{E(c["hint"])}</small></span></label>\n' for c in d["size_chips"])
    p = re.sub(r'(<div class="chips">\n)(?:\s*<label class="chip">.*?</label>\n)+', lambda m: m.group(1) + chips, p, flags=re.S)
    if any("$" in c["value"] for c in d["size_chips"]):  # budget chips: the question is the budget, not the size
        p = p.replace("<legend>Roughly how big is the job?</legend>", "<legend>What's your budget?</legend>")
    p = p.replace("e.g. Feilding or Kelvin Grove", E(d["suburb_example"]))
    p = p.replace("e.g. a concrete pad for a garden shed", E(d["other_example"]))

    # --- trust strip ---
    icons = ["star", "clock", "hammer", "shield"]
    lis = "".join(f'    <li><span class="ic"><svg class="i"><use href="#i-{icons[i % 4]}"/></svg></span>'
                  f'<span><b>{E(x["num"])}</b>{E(x["label"])}</span></li>\n' for i, x in enumerate(d["trust"]))
    p = _between(p, "<!-- Trust strip -->", "<!-- 3. WHY WORK WITH US -->",
                 f'<!-- Trust strip -->\n<div class="trust">\n  <ul class="wrap">\n{lis}  </ul>\n</div>\n\n' if lis else "")

    # --- why us ---
    w = d["why"]
    stats = "".join(f'        <div><b>{E(s["num"])}</b><span>{E(s["label"])}</span></div>\n' for s in w.get("stats", []))
    stats = f'      <div class="why-stats">\n{stats}      </div>\n' if stats else ""
    cards = "".join(
        f'        <div class="why-card"><span class="ic"><svg class="i"><use href="#i-{c["icon"] if c["icon"] in ICONS else "check"}"/></svg></span>'
        f'<div><h3>{E(c["h"])}</h3><p>{E(c["p"])}</p></div></div>\n' for c in w["cards"])
    wp = ph[d["why_photo"]] if ph else None
    figure = (f'''      <figure class="why-photo" style="margin:0">
        <img src="img/work-{d["why_photo"]}-900.webp" srcset="img/work-{d["why_photo"]}-480.webp 480w, img/work-{d["why_photo"]}-900.webp 900w" sizes="(min-width:1000px) 760px, 100vw" alt="{E(wp["alt"])}" loading="lazy" width="{wp["w9"]}" height="{wp["h9"]}">
        <figcaption>{E(wp["label"])}</figcaption>
      </figure>
''' if wp else "")
    panel = (f'    <div class="why-panel{" has-stats" if figure and stats else ""}">\n{figure}{stats}    </div>\n'
             if figure or stats else "")
    p = _between(p, "<!-- 3. WHY WORK WITH US -->", "<!-- 4. TESTIMONIALS -->", f'''<!-- 3. WHY WORK WITH US -->
<section class="sec" id="why">
  <div class="wrap">
    <div class="why-head">
      <div class="sec-head">
        <span class="eyebrow">Why work with us</span>
        <h2>{E(w["heading"])}</h2>
      </div>
      <p>{E(w["intro"])}</p>
    </div>
{panel}    <div class="why-cards">
{cards}    </div>
    <div class="why-cta"><a href="#quote" class="btn btn-accent">{E(w.get("cta") or "Book a free quote")}</a></div>
  </div>
</section>

''')

    # --- reviews (only real, supplied reviews; otherwise the section is removed) ---
    if d.get("reviews"):
        src = d.get("review_source") or ""
        icon = {"facebook": "i-facebook", "google": "i-google"}.get(src.lower())
        srcmark = f'<svg class="src" aria-hidden="true"><use href="#{icon}"/></svg>' if icon else ""
        arts = "".join(
            f'      <article class="rev"><span class="stars" aria-label="5 stars">{_stars()}</span><p>"{E(r["text"])}"</p>'
            f'<footer>{E(r.get("author", ""))}</footer></article>\n' for r in d["reviews"])
        rev = f'''<!-- 4. TESTIMONIALS -->
<section class="sec sec-grey" id="reviews">
  <div class="wrap">
    <div class="rev-top">
      <div class="sec-head" style="margin:0;flex:1 1 320px">
        <span class="eyebrow">Testimonials</span>
        <h2 style="margin:0">{E(d["reviews_heading"])}</h2>
      </div>
      <div class="rev-score"><b>5.0</b><div><span class="stars" aria-label="5 out of 5 stars">{_stars()}</span><small>{srcmark}{E(d.get("review_count_label") or "")}</small></div></div>
    </div>
    <div class="rev-track">
{arts}    </div>
    <p class="swipe-hint">Swipe for more reviews →</p>
  </div>
</section>

'''
    else:
        rev = "<!-- 4. TESTIMONIALS -->\n"
    p = _between(p, "<!-- 4. TESTIMONIALS -->", "<!-- 5. OUR WORK -->", rev)

    # --- work (default order; each page re-renders it with its own order) ---
    p = _between(p, "<!-- 5. OUR WORK -->", "<!-- 6. WHAT WE DO -->", "<!-- 5. OUR WORK -->\n{{WORK}}\n")

    # --- services ---
    s = d["services"]
    cards = "".join(
        f'      <article class="svc"><img src="img/work-{c["photo"]}-480.webp" srcset="img/work-{c["photo"]}-480.webp 480w, '
        f'img/work-{c["photo"]}-900.webp 900w" sizes="(min-width:1000px) 370px, (min-width:640px) 50vw, 100vw" '
        f'alt="{E(ph[c["photo"]]["alt"])}" loading="lazy" width="{ph[c["photo"]]["w"]}" height="{ph[c["photo"]]["h"]}">'
        f'<div class="svc-body"><h3>{E(c["title"])}</h3><p>{E(c["body"])}</p>'
        f'<button type="button" class="svc-link" data-service="{E(c["service"])}">Quote this job →</button></div></article>\n'
        for c in s["cards"] if 0 <= c["photo"] < len(ph))
    p = _between(p, "<!-- 6. WHAT WE DO -->", "{{FAQ}}", f'''<!-- 6. WHAT WE DO -->
<section class="sec sec-grey" id="services">
  <div class="wrap">
    <div class="sec-head">
      <span class="eyebrow">What we do</span>
      <h2>{E(s["heading"])}</h2>
      <p>{E(s["intro"])}</p>
    </div>
    <div class="svc-grid">
{cards}    </div>
  </div>
</section>

''')

    # --- contact (left column) ---
    c = d["contact"]
    ticks = "".join(f'        <li><svg class="i"><use href="#i-check"/></svg>{E(t)}</li>\n' for t in c["ticks"])
    left = f'''<div class="wrap contact-grid">
    <div>
      <span class="eyebrow" style="color:var(--accent)">Contact us</span>
      <h2>{E(c["heading"])}</h2>
      <ul class="ticks">
{ticks}      </ul>
      <p style="margin:0">Prefer to talk? Give us a call:</p>
      <a href="tel:{d["phone_e164"]}" class="big-phone" data-call="contact"><svg class="i"><use href="#i-phone"/></svg>{E(d["phone_display"])}</a>
      <div class="contact-meta">
        <div><b>Area we cover</b>{E(c["area"])}</div>
        <div><b>Response time</b>{E(c["response"])}</div>
      </div>
    </div>

'''
    p = _between(p, '<div class="wrap contact-grid">', '    <div class="form-card" id="quote-2">', left)

    # --- footer ---
    p = re.sub(r'<p style="margin:0">palmerstonnorthconcreting\.co\.nz is owned.*?</p>',
               f'<p style="margin:0">{d["footer_html"]}</p>', p, flags=re.S)
    if not d.get("has_legal"):
        p = re.sub(r'<nav aria-label="Legal">.*?</nav>', "", p, flags=re.S)
        p = re.sub(r"<br>By sending you agree to our <a href=\"/privacy-policy\"[^>]*>Privacy Policy</a>\.", "", p)

    p = p.replace("Palmerston North", E(city))
    return p


def fill_page(master, d, page, work_html):
    """One landing page from the client master + its copy."""
    p = master.replace("{{WORK}}", work_html)
    ticks = "\n".join(f'        <li><svg class="i"><use href="#i-check"/></svg>{E(t)}</li>' for t in page["ticks"])
    faq = "".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in page["faq"])
    faq_sec = (f'<section class="sec" id="faq">\n  <div class="wrap">\n    <div class="sec-head"><span class="eyebrow">FAQs</span>'
               f'<h2>Good questions</h2></div>\n    <div class="faq">{faq}</div>\n  </div>\n</section>\n') if page["faq"] else ""
    if not page["faq"]:
        p = p.replace('<a href="#faq">FAQs</a>', "")
    for k, v in {"{{TITLE}}": E(page["title"]), "{{DESC}}": E(page["desc"]), "{{H1}}": E(page["h1"]),
                 "{{SUB}}": E(page["sub"]), "{{TICKS}}": ticks, "{{FAQ}}": faq_sec}.items():
        p = p.replace(k, v)
    ex = (page.get("other_example") or "").strip()
    if ex:  # the "What's the job?" helper text must relate to THIS page's service, not the site-wide example
        p = p.replace(f'placeholder="{E(d["other_example"])}"', f'placeholder="{E(ex)}"')
    sel = page.get("select") or ""
    if sel:
        p = p.replace('<option value="" disabled selected>Choose a job type</option>',
                      '<option value="" disabled>Choose a job type</option>')
        p = p.replace(f"<option>{E(sel)}</option>", f"<option selected>{E(sel)}</option>")
    hero = page["hero_stem"]
    p = p.replace("img/hero-crew-screeding", f"img/{hero}")
    return no_dashes(p)


def hero_markup_check(p):
    return "img/hero-" in p or "hero-bg" in p


def leftovers(page_html, own_text=""):
    """Template-client strings still present in visible HTML (should be none).

    own_text is the client's own name and service areas: a template word that
    appears there is the client's real place name (e.g. a Palmerston North
    client), not a leak."""
    own = own_text.lower()
    return sorted({s for s in LEAKS if s in page_html and s.lower() not in own})


# ---------- legal pages ----------

ART_CSS = (".article{max-width:780px}.article h2{font-size:clamp(22px,3vw,28px);margin:1.8em 0 .5em}"
           ".article p,.article li{font-size:17px}.article ul,.article ol{padding-left:1.25em;margin:0 0 1.2em}"
           ".article li{margin-bottom:.6em}")


def legal_page(master, d, title, h1, body_html):
    """Terms/privacy page wearing the client's own header + footer."""
    head_end = master.index("</style>")
    head = master[:head_end] + ART_CSS
    head = re.sub(r"<title>.*?</title>", f"<title>{E(title)} | {E(d['name'])}</title>", head, count=1)
    head = re.sub(r'<meta name="description" content="[^"]*">',
                  f'<meta name="description" content="{E(title)} for {E(d["name"])}.">', head, count=1)
    head = re.sub(r'<link rel="preload" as="image"[^>]*>\n?', "", head)
    nav_to_main = master[head_end:master.index('<main id="top">')].replace('href="#', 'href="/#')
    footer = master[master.index("</main>"):]
    footer = footer[:footer.index("<script>")] + "</body>\n</html>\n"
    page = (head + nav_to_main + f'<main id="top">\n<section class="sec">\n  <div class="wrap">\n    <article class="article">\n'
            f'      <span class="eyebrow">Legal</span>\n      <h1>{E(h1)}</h1>\n      {body_html}\n    </article>\n  </div>\n</section>\n'
            + footer)
    page = re.sub(r"(?<![\w/.-])img/", "/quote/img/", page)
    return no_dashes(page)
