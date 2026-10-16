"""Step 6 in the app (data key "step5") - Landing pages.

Three ways to get landing pages (chosen in the web app):
  build_template  Option 1. All pages built from the LFT site template, template
                  styling untouched; plus privacy, terms and index from the template.
  build_designed  Option 2. Same pages, re-skinned with the client's own logo,
                  fonts and colours read from their website; privacy and terms are
                  copied straight from that website. Landing pages + index only.
  urls            Option 3. The user pastes the links; nothing is built.

A build clones the template, writes the client's pages (landing pages are
Claude's copy placed into the template's own HTML; no layout is generated),
pushes them to a new private GitHub repo, deploys them to a new Netlify site and
publishes the links for review. Approving then runs link_urls.link_landing_pages.
"""

import json
import os
import re
import shutil
import tempfile
import time

from .. import config, llm
from ..jobs import Blocked, register_step
from . import lp_brand, lp_publish, lp_site, store

MAX_PHOTOS = 36
PHOTO_BATCH = 12
BUILD_MODES = ("build_template", "build_designed")
LFT_NBZN = "9429052803291"

COPY_RULES = """\
You write copy for Google Ads landing pages for a New Zealand trade business.
- NZ English. Never use em dashes or en dashes (use a comma or full stop).
- Use ONLY facts given in "facts" (years, counts, guarantees, areas, services). Never invent a
  number, price, licence, guarantee, award, review or suburb. If a fact is missing, leave that
  item out rather than guessing.
- Only the services listed in facts.services. Never add an adjacent trade.
- Never use the words cheap, affordable, budget or discount.
- Plain, direct, local. No hype words, no "premier", "unparalleled", "state of the art".
- Answer with JSON only."""


# ---------- inputs ----------

def _resolve(path):
    if not path:
        return None
    if os.path.isabs(path) and os.path.exists(path):
        return path
    p = os.path.join(config.WEB_DATA_ROOT, path)
    return p if os.path.exists(p) else None


def _phone(raw):
    m = re.search(r"(?:\+?64|0)[\d\s\-()]{7,}\d", raw or "")
    if not m:
        return None, None
    disp = re.sub(r"\s+", " ", m.group(0)).strip()
    digits = re.sub(r"\D", "", disp)
    e164 = "+" + digits if digits.startswith("64") else "+64" + digits.lstrip("0")
    return disp, e164


def _facts(s0):
    keys = ("business_name", "services", "service_areas", "years_experience", "completed_projects", "reviews",
            "differentiators", "certifications", "owner_name", "other_info", "scope_notes")
    return {k: s0[k] for k in keys if s0.get(k)}


def _pages_arg(ad_groups):
    return [g["name"] for g in ad_groups]


# ---------- Claude calls ----------

def _caption_photos(ctx, photos, trade_hint):
    """Vision pass: a short factual caption + label per photo (used for alt text,
    gallery labels and picking each page's hero)."""
    out = {}
    for start in range(0, len(photos), PHOTO_BATCH):
        batch = photos[start:start + PHOTO_BATCH]
        content = []
        for i, ph in enumerate(batch, start):
            content.append({"type": "text", "text": f"Photo {i}:"})
            content.append(llm.image_block(ph["thumb"]))
        content.append({"type": "text", "text": (
            f"These are real job photos from a New Zealand {trade_hint} business. For each photo give: "
            '"alt" (one factual sentence describing what is visibly there; no location, brand or claim), '
            '"label" (2-4 word job type, e.g. "Driveway", "Exterior repaint"), '
            '"service" (which job it shows, short). Return JSON: [{"i": <photo number>, "alt": "", "label": "", "service": ""}]')})
        for row in llm.complete_json(ctx, COPY_RULES, content, max_tokens=3000):
            out[int(row["i"])] = row
        ctx.log(f"Captioned photos {start + 1}-{start + len(batch)}")
    return out


def _site_copy(ctx, facts, city, photos, note):
    cap = "\n".join(f'{i}: {p["label"]} - {p["alt"]}' for i, p in enumerate(photos))
    user = f"""facts: {json.dumps(facts, indent=1)}
city (main service area): {city}
photos (index: label - description):
{cap}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Write the shared sections of the landing page. Return JSON:
{{
 "job_options": ["4-8 customer-facing job names from the stated services, then 'Something else' last"],
 "size_chips": [{{"value":"Small (under 25m2)","label":"Small","hint":"under 25m²"}}, 3 more; the last is {{"value":"Not sure","label":"Not sure","hint":"we'll measure"}}; default is m2; but pick the unit the customer would measure THIS trade in: metres for linear jobs (fences, retaining walls, gutters; chips like "Short (under 20m)", hint "under 20m", never m2), m2 for area jobs, and for renovations/bathrooms with no sensible measure use budget chips instead ("Under $10k", "$10k to $20k", "$20k+", then Not sure)],
 "suburb_example": "e.g. <two real towns/suburbs from the service areas>",
 "other_example": "e.g. <a small job in this trade>",
 "trust": [2-4 of {{"num":"12+ yrs","label":"industry experience"}}; ONLY from facts],
 "why": {{"heading":"","intro":"","stats":[0-2 {{"num":"","label":""}} from facts],
          "cards":[4 x {{"icon":"doc|user|rain|shield|clock|hammer|truck|pin","h":"","p":""}}],"cta":""}},
 "why_photo": <photo index>,
 "work": {{"heading":"Recent jobs around {city}","intro":""}},
 "services": {{"heading":"","intro":"","cards":[4-6 x {{"title":"","body":"","service":"<exactly one of job_options>","photo":<photo index showing that job>}}]}},
 "contact": {{"heading":"","ticks":[3],"area":"<areas from facts>","response":"<only if in facts, else 'We reply to every enquiry as soon as we can.'>"}},
 "reviews_heading": "What {city} customers say",
 "trade_contractor": "e.g. concrete contractor",
 "trade_services": "e.g. concrete or concrete services"
}}"""
    return llm.complete_json(ctx, COPY_RULES, user, max_tokens=4500)


def _group_pages(ctx, facts, ad_groups, job_options, note):
    user = f"""facts.services: {json.dumps(facts.get("services"))}
job_options: {json.dumps(job_options)}
ad groups: {json.dumps(_pages_arg(ad_groups))}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Group these ad groups into landing pages, one page per distinct service. Generic ad groups
(contractors, companies, general costs) share ONE general page (general: true, exactly one).
Every ad group appears exactly once. At most 10 pages. Return JSON:
{{"pages":[{{"slug":"kebab-case-max-40","name":"Service name","ad_groups":["exact ad group name"],
 "general":false,"select":"<one of job_options matching this page, or '' for the general page>"}}]}}"""
    pages = llm.complete_json(ctx, COPY_RULES, user, max_tokens=3000)["pages"]
    assigned = {n for p in pages for n in p["ad_groups"]}
    for g in ad_groups:  # never drop an ad group
        if g["name"] not in assigned:
            gen = next((p for p in pages if p.get("general")), pages[0])
            gen["ad_groups"].append(g["name"])
    if not any(p.get("general") for p in pages):
        pages[0]["general"] = True
    return pages


def _page_copy(ctx, facts, city, page, photos, job_options, other_titles, note):
    cap = "\n".join(f'{i}: {p["label"]} - {p["alt"]}' for i, p in enumerate(photos))
    user = f"""facts: {json.dumps(facts, indent=1)}
city: {city}
This landing page: {page["name"]} (general page: {bool(page.get("general"))}); ad groups sent here: {page["ad_groups"]}
Other pages' titles (do not duplicate): {other_titles}
photos:
{cap}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Return JSON:
{{"title":"<=60 chars, ends with ', {city}'","desc":"130-155 chars, mentions {facts.get('business_name')}",
 "h1":"<Service> in {city}","sub":"one sentence on what the customer gets",
 "ticks":[4 short benefit lines using only facts],
 "faq":[[question, answer] x 10; answers 25-60 words, honest, no prices or invented guarantees],
 "hero_photo": <index of the best photo for this page>,
 "photo_order": [photo indexes, most relevant to this page first]}}"""
    return llm.complete_json(ctx, COPY_RULES, user, max_tokens=4000)


def _fix_page(ctx, facts, city, page, photos, job_options, other_titles, note, copy):
    for _ in range(2):
        problems = []
        if len(copy.get("title", "")) > 60:
            problems.append(f'title is {len(copy["title"])} chars, max 60')
        if not 120 <= len(copy.get("desc", "")) <= 160:
            problems.append(f'desc is {len(copy.get("desc", ""))} chars, need 130-155')
        if len(copy.get("ticks", [])) != 4:
            problems.append("need exactly 4 ticks")
        if len(copy.get("faq", [])) < 8:
            problems.append("need at least 8 FAQs")
        if not problems:
            break
        ctx.log(f'{page["name"]}: fixing {"; ".join(problems)}')
        copy = _page_copy(ctx, facts, city, page, photos, job_options, other_titles,
                          (note + " | " if note else "") + "FIX: " + "; ".join(problems))
    return copy


def _plan(ctx, s0, ad_groups, note):
    """Which landing pages will be built and which ad groups each one serves.
    Shown to the user before anything is built."""
    opts = [str(x) for x in (s0.get("services") or [])][:7] + ["Something else"]
    pages = _group_pages(ctx, _facts(s0), ad_groups, opts, note)
    out, seen = [], set()
    for p in pages:
        slug = re.sub(r"[^a-z0-9-]+", "-", str(p.get("slug", "")).lower()).strip("-")[:40] or "page"
        while slug in seen:
            slug += "-2"
        seen.add(slug)
        out.append({"slug": slug, "name": str(p.get("name") or slug), "ad_groups": p["ad_groups"],
                    "general": bool(p.get("general")), "select": p.get("select") or ""})
    return out


def _apply_plan(plan, ad_groups, job_options):
    """The approved plan, kept in line with the current ad groups (deleted ones
    dropped, new ones go on the general page). None if there is no plan."""
    if not plan or not plan.get("pages"):
        return None
    names = {g["name"] for g in ad_groups}
    pages = []
    for p in plan["pages"]:
        ags = [n for n in p.get("ad_groups", []) if n in names]
        if not ags:
            continue
        sel = p.get("select") or ""
        if sel not in job_options:
            sel = next((o for o in job_options if o.lower() == str(p.get("name", "")).lower()), "")
        pages.append({**p, "ad_groups": ags, "select": sel})
    if not pages:
        return None
    assigned = {n for p in pages for n in p["ad_groups"]}
    gen = next((p for p in pages if p.get("general")), pages[0])
    gen["general"] = True
    for g in ad_groups:
        if g["name"] not in assigned:
            gen["ad_groups"].append(g["name"])
    return pages


def _brand_tokens(ctx, dg):
    user = f"""Website: {dg["title"]}
Most used colours (hex, by frequency): {dg["colours"]}
Colours from named brand variables: {dg["named_colours"]}  theme-color: {dg["theme_color"]}
Font families seen (most used first, already cleaned to Google Fonts names): {dg["fonts"]}   Google Fonts links: {dg["google_fonts"]}
Logo candidates: {dg["logo_candidates"]}
Header HTML (first part of page): {dg["home_html"][:5000]}

Pick this business's design tokens. "accent" is the main button/highlight colour, "ink" the very dark
colour used for headings and the dark bands (if the site has no dark brand colour use #16181B),
"steel" a slightly lighter dark. Fonts only count if they are on Google Fonts, otherwise "".
Use the font the site really uses for headings and for body text; if it uses one family for both, or you can't tell, use the most-used family for both.
Return JSON: {{"accent":"#rrggbb","accent_dark":"#rrggbb (10-15% darker)","ink":"#rrggbb","steel":"#rrggbb",
"head_font":"Family or ''","body_font":"Family or ''","logo_url":"best logo URL from candidates or ''"}}"""
    return llm.complete_json(ctx, "You extract brand design tokens from a website. JSON only.", user, max_tokens=800)


# ---------- build ----------

def _hex_ok(v):
    return isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)


def _load_logo(s0, dg, token_logo):
    """(PIL image or None, svg_bytes or None)."""
    from PIL import Image
    p = _resolve(s0.get("business_logo_path"))
    if p:
        if p.lower().endswith(".svg"):
            return None, open(p, "rb").read()
        return Image.open(p).convert("RGBA"), None
    for url in ([token_logo] if token_logo else []) + (dg["logo_candidates"] if dg else []):
        try:
            data, ctype = lp_brand.fetch(url, binary=True)
            if "svg" in ctype or url.lower().split("?")[0].endswith(".svg"):
                return None, data
            im = Image.open(__import__("io").BytesIO(data)).convert("RGBA")
            if im.width >= 60:
                return im, None
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
    return None, None


def _logo_is_light(im):
    """True when the logo's visible pixels are mostly light (white-on-dark logos
    vanish on the template's white nav)."""
    px = [p for p in im.convert("RGBA").getdata() if p[3] > 60]
    if not px:
        return False
    return sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _ in px) / len(px) > 170


def _load_favicon(dg):
    """The client's own favicon from their live site (largest first), or None."""
    from PIL import Image
    for url in dg.get("favicon_candidates", []):
        try:
            data, ctype = lp_brand.fetch(url, binary=True, limit=2_000_000)
            if "svg" in ctype or "html" in ctype:
                continue
            im = Image.open(__import__("io").BytesIO(data)).convert("RGBA")
            if im.width >= 32:
                return im
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
    return None


def _collect_photos(s0, dg):
    from PIL import Image
    ims = []
    for path in (s0.get("work_photo_paths") or [])[:MAX_PHOTOS]:
        p = _resolve(path)
        if p:
            try:
                ims.append(lp_site.load_image(p))
            except Exception:  # noqa: BLE001
                pass
    if len(ims) < 6 and dg:  # client site images, only if they haven't supplied their own
        for url in dg["images"]:
            if len(ims) >= 24:
                break
            try:
                data, _ = lp_brand.fetch(url, binary=True, limit=6_000_000)
                im = lp_site.load_image(data)
                if im.width >= 600 and im.height >= 350:
                    ims.append(im)
            except Exception:  # noqa: BLE001
                continue
    return ims


def build(ctx, s5, s0, ad_groups, note):
    mode = s5["mode"]
    designed = mode == "build_designed"
    pid = ctx.project_id

    missing = lp_publish.missing_tokens()
    if missing:
        raise Blocked("Landing page builds need " + " and ".join(missing) + " set in Railway Variables "
                      "(see DEPLOY.md). Add them and press Retry.")
    name = s0.get("business_name")
    areas = s0.get("service_areas") or []
    phone_disp, phone_e164 = _phone(s0.get("business_phone"))
    if not (name and s0.get("services") and areas):
        raise Blocked("I need the business name, services and service area under 'Business info' before I can build pages.")
    if not phone_disp:
        raise Blocked("I need the business phone number under 'Business info' (it goes on every landing page).")
    if designed and not s5.get("design_source_url"):
        raise Blocked("Add the client's existing website link on the Landing Pages step first.")
    city = areas[0]
    facts = _facts(s0)
    work = tempfile.mkdtemp(prefix="lp-")
    try:
        # 1. template + brand
        tpl = os.path.join(work, "template")
        lp_publish.clone_template(tpl)
        master_src = open(os.path.join(tpl, "content", "lp-master.html"), encoding="utf-8").read()
        dg = tokens = None
        brand_logo = ""
        if designed:
            ctx.log(f"Reading {s5['design_source_url']}")
            dg = lp_brand.digest(s5["design_source_url"])
            t = _brand_tokens(ctx, dg)
            tokens = {k: t[k] for k in ("accent", "accent_dark", "ink", "steel") if _hex_ok(t.get(k))}
            # Dark brand colour from the site's CSS too (Claude falls back to the template's #16181B).
            darks = dg.get("dark_colours") or []
            neutral = [c for c in darks if max(int(c[i:i + 2], 16) for i in (1, 3, 5)) - min(int(c[i:i + 2], 16) for i in (1, 3, 5)) <= 40]
            pair = sorted((neutral or darks)[:2], key=lambda c: sum(int(c[i:i + 2], 16) for i in (1, 3, 5)))
            if pair:
                tokens["ink"] = pair[0]
                tokens["steel"] = pair[1] if len(pair) > 1 else "#" + "".join(
                    "%02x" % min(255, int(pair[0][i:i + 2], 16) + 20) for i in (1, 3, 5))
            # Fonts come from the site's CSS, not from Claude (it picks a secondary font as the heading font).
            # One family for both unless the site styles h1-h3 with a different one.
            bf = dg["fonts"][0] if dg["fonts"] else (t.get("body_font") or t.get("head_font"))
            hf = dg.get("heading_font") or bf
            if hf and bf:
                t["head_font"], t["body_font"] = hf, bf
                tokens.update(head_font=t["head_font"], body_font=t["body_font"],
                              fonts_url=lp_brand.google_fonts_url(t["head_font"], t["body_font"]))
            brand_logo = t.get("logo_url") or ""
            ctx.log(f"Brand: {tokens}")

        # 2. site + deploy target
        site = lp_publish.ensure_netlify_site(lp_publish.repo_name_for(name), s5.get("netlify_site_id"))
        host = (s5.get("custom_domain") or "").strip().lower() or site["url"].replace("https://", "")
        # Links point at Netlify until the user confirms DNS is connected (custom domain 404s before then).
        base = site["url"]
        custom_base = "https://" + host if s5.get("custom_domain") else ""
        out = os.path.join(work, "site")
        qimg = os.path.join(out, "quote", "img")
        os.makedirs(qimg)

        # 3. logo + photos
        logo_im, logo_svg = _load_logo(s0, dg, brand_logo)
        if logo_im is None and logo_svg is None:
            raise Blocked("I couldn't find a logo. Upload one under 'Business info' and press Retry.")
        logo_light = _logo_is_light(logo_im) if logo_im is not None else False
        if logo_svg:
            open(os.path.join(qimg, "logo.svg"), "wb").write(logo_svg)
            logo_file, logo_w, logo_h = "logo.svg", 244, 54
            icon_im = None
        else:
            logo_im.thumbnail((600, 160))
            logo_im.save(os.path.join(qimg, "logo.png"))
            logo_file, logo_h = "logo.png", 54
            logo_w = max(40, round(54 * logo_im.width / logo_im.height))
            icon_im = logo_im
        fav_im = _load_favicon(dg) if dg else None
        if fav_im is not None:
            icon_im = fav_im
        raw = _collect_photos(s0, dg)
        if len(raw) < 3:
            raise Blocked("Landing pages need at least 3 real job photos. Upload some under 'Business info' and press Retry.")
        photos = []
        for i, im in enumerate(raw):
            sizes = lp_site.save_sizes(im, qimg, f"work-{i}", (480, 900))
            photos.append({"thumb": lp_site.jpeg_thumb(im), "w": sizes[480][0], "h": sizes[480][1],
                           "w9": sizes[900][0], "h9": sizes[900][1], "label": "", "alt": ""})
        trade_hint = ", ".join(s0["services"][:3])
        caps = _caption_photos(ctx, photos, trade_hint)
        for i, ph in enumerate(photos):
            c = caps.get(i, {})
            ph["label"] = c.get("label") or "Our work"
            ph["alt"] = lp_site.no_dashes(c.get("alt") or f"Recent {trade_hint} job")

        # 4. copy
        copy = _site_copy(ctx, facts, city, photos, note)
        job_options = [o for o in copy["job_options"] if o != "Something else"][:7] + ["Something else"]
        n = len(photos)
        clamp = lambda v: v if isinstance(v, int) and 0 <= v < n else 0  # noqa: E731
        for c in copy["services"]["cards"]:
            c["photo"] = clamp(c.get("photo"))
            if c.get("service") not in job_options:
                c["service"] = job_options[0]
        pages = _apply_plan(s5.get("plan"), ad_groups, job_options) or _group_pages(ctx, facts, ad_groups, job_options, note)
        titles = []
        for pg in pages:
            pg["copy"] = _fix_page(ctx, facts, city, pg, photos, job_options, titles, note,
                                   _page_copy(ctx, facts, city, pg, photos, job_options, titles, note))
            titles.append(pg["copy"]["title"])
            ctx.log(f'Wrote page copy: {pg["slug"]}')

        reviews = [r for r in (s0.get("review_quotes") or []) if isinstance(r, dict) and r.get("text")]
        year = time.strftime("%Y")
        d = {
            "name": name, "city": city, "phone_display": phone_disp, "phone_e164": phone_e164,
            "gtm_id": s0.get("gtm_container_id"), "photos": photos, "job_options": job_options,
            "size_chips": copy["size_chips"][:4], "suburb_example": copy["suburb_example"],
            "other_example": copy["other_example"], "trust": copy.get("trust", [])[:4],
            "why": copy["why"], "why_photo": clamp(copy.get("why_photo")), "work": copy["work"],
            "services": copy["services"], "contact": copy["contact"],
            "reviews": reviews, "reviews_heading": copy.get("reviews_heading", ""),
            "review_source": s0.get("review_source", ""), "review_count_label": s0.get("review_count_label", ""),
            "rating_line": s0.get("rating_line", ""),
            "logo_file": logo_file, "logo_w": logo_w, "logo_h": logo_h, "tokens": tokens,
            "logo_light": logo_light,
            "has_legal": True,
            "footer_html": (f"&copy; {year} {lp_site.E(name)}. All rights reserved." if designed else
                            f"{lp_site.E(host)} is owned and operated by Leads For Tradies Limited (NZBN: {LFT_NBZN}). "
                            f"Services on this site are fulfilled by our authorised local trade partner, {lp_site.E(name)}."),
        }

        # 5. legal pages
        legal, warnings = {}, []
        if designed:
            found = lp_brand.find_legal(dg["home_html"], s5["design_source_url"])
            for key, label in (("privacy", "Privacy Policy"), ("terms", "Terms and Conditions")):
                body = ""
                if found[key]:
                    try:
                        body = lp_brand.extract_legal_body(lp_brand.fetch(found[key]), found[key])
                    except Exception as exc:  # noqa: BLE001
                        ctx.log(f"Couldn't read {found[key]}: {exc}")
                if body:
                    legal[key] = (label, body)
                else:
                    warnings.append(f"Couldn't copy the client's {label.lower()} from their site; add it by hand.")
            d["has_legal"] = len(legal) == 2
        else:
            today = time.strftime("%-d %B %Y")
            tok = {"{{DOMAIN}}": host, "{{PARTNER}}": name, "{{TRADE_CONTRACTOR}}": copy["trade_contractor"],
                   "{{TRADE_SERVICES}}": copy["trade_services"], "{{EFFECTIVE_DATE}}": today}
            for key, label, f in (("privacy", "Privacy Policy", "legal-privacy.html"),
                                  ("terms", "Terms & Disclosures", "legal-terms.html")):
                body = open(os.path.join(tpl, "content", f), encoding="utf-8").read()
                for k, v in tok.items():
                    body = body.replace(k, lp_site.E(v))
                legal[key] = (label, body)

        # 6. assemble
        master = lp_site.build_master(master_src, d)
        lp_site.save_sizes(raw[d["why_photo"]], qimg, "contact-bg", (900, 1600))
        general = next(p for p in pages if p.get("general"))
        urls = {}
        for pg in pages:
            c = pg["copy"]
            hero = clamp(c.get("hero_photo"))
            lp_site.save_sizes(raw[hero], qimg, f"hero-{hero}", (900, 1600))
            page = lp_site.fill_page(master, d, {**c, "select": pg.get("select") if pg.get("select") in job_options else "",
                                                  "hero_stem": f"hero-{hero}"},
                                     lp_site.work_section(d, c.get("photo_order")))
            left = lp_site.leftovers(re.sub(r"<(style|script)\b.*?</\1>", "", page, flags=re.S),
                                     " ".join([name or "", *map(str, areas)]))
            if left:  # warn, don't fail: the whole build (and its Claude spend) shouldn't be lost for a few words
                warnings.append(f"The page '{pg['name']}' still contains words from the template's old client "
                                f"({', '.join(left)}). Check it; if they're wrong, use Request changes and say what "
                                f"to put there instead.")
            open(os.path.join(out, "quote", pg["slug"] + ".html"), "w", encoding="utf-8").write(page)
            urls[pg["slug"]] = f"{base}/quote/{pg['slug']}"
            if pg is general:
                idx = re.sub(r"(?<![\w/.-])img/", "/quote/img/", page)
                open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(idx)
        for key, fname in (("privacy", "privacy-policy.html"), ("terms", "terms.html")):
            if key in legal:
                label, body = legal[key]
                html_ = lp_site.legal_page(master.replace("{{WORK}}", ""), d, label, label, body)
                open(os.path.join(out, fname), "w", encoding="utf-8").write(html_)

        # 7. static files from the template + icons
        os.makedirs(os.path.join(out, "img"), exist_ok=True)
        if icon_im is not None:
            lp_site.write_icons(icon_im, os.path.join(out, "img"), out, bare=fav_im is not None)
        # the template repo renamed site/ to base-site/; accept either
        tpl_site = next(d for d in (os.path.join(tpl, "base-site"), os.path.join(tpl, "site"))
                        if os.path.isdir(d))
        shutil.copytree(os.path.join(tpl_site, "netlify"), os.path.join(out, "netlify"))
        shutil.copy(os.path.join(tpl_site, "_headers"), os.path.join(out, "_headers"))
        open(os.path.join(out, "netlify.toml"), "w").write(
            '[build]\n  publish = "."\n\n[functions]\n  directory = "netlify/functions"\n')
        open(os.path.join(out, "robots.txt"), "w").write("User-agent: *\nAllow: /\nDisallow: /api/\n")

        # A page pointing at an image we didn't write would ship a broken picture.
        for fname in [f for f in os.listdir(out) if f.endswith(".html")] + \
                ["quote/" + f for f in os.listdir(os.path.join(out, "quote")) if f.endswith(".html")]:
            html_ = open(os.path.join(out, fname), encoding="utf-8").read()
            for ref in set(re.findall(r'(?<![\w/.-])/?((?:quote/)?img/[\w.-]+\.(?:webp|png|jpg|svg))', html_)):
                where = ref if ref.startswith("quote/") else ("quote/" + ref if fname.startswith("quote/") else ref)
                if not os.path.exists(os.path.join(out, where)) and not os.path.exists(os.path.join(out, ref)):
                    raise RuntimeError(f"{fname} references missing image {ref}")

        # 8. publish
        ctx.log("Pushing to GitHub")
        prev_repo = s5.get("repo_url") or ""
        repo, repo_path = lp_publish.push_repo(
            out, prev_repo.replace("https://github.com/" + lp_publish.OWNER + "/", "") or lp_publish.repo_name_for(name),
            f"Landing pages for {name}", reuse=bool(prev_repo))
        ctx.log("Linking the repo to Netlify (deploys from GitHub)")
        lp_publish.link_repo(site["id"], repo_path)
        if s5.get("custom_domain"):
            try:
                lp_publish.set_custom_domain(site["id"], host)
            except lp_publish.PublishError as exc:
                warnings.append(f"Couldn't attach {host} to Netlify automatically ({exc}); add it in Netlify > Domain management.")

        # Ad copy and sitelinks always get the FINAL domain links, never the temporary Netlify ones.
        ad_base = custom_base or base
        ad_urls = {n_: f"{ad_base}/quote/{pg['slug']}" for pg in pages for n_ in pg["ad_groups"]}
        netlify_host = site["url"].replace("https://", "")
        dns_note = (f"Point a CNAME for {host} at {netlify_host}, then wait for the HTTPS certificate."
                    if s5.get("custom_domain") else "")
        return {
            "ad_groups": [{"name": g["name"], "url": ad_urls.get(g["name"], "")} for g in ad_groups],
            "pages": [{"slug": pg["slug"], "name": pg["name"], "title": pg["copy"]["title"],
                       "url": urls[pg["slug"]], "ad_groups": pg["ad_groups"], "general": bool(pg.get("general"))}
                      for pg in pages],
            "index_url": base + "/", "privacy_url": base + "/privacy-policy" if "privacy" in legal else "",
            "terms_url": base + "/terms" if "terms" in legal else "",
            "repo_url": repo, "netlify_site_id": site["id"], "site_host": host, "dns_note": dns_note,
            "preview_base": base, "netlify_base": site["url"], "custom_base": custom_base, "domain_connected": False,
            "warnings": warnings, "built_at": time.strftime("%Y-%m-%d %H:%M"),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- handler ----------

def _seed_groups(pid, s5):
    existing = {g["name"]: g.get("url", "") for g in (s5.get("ad_groups") or [])}
    s4 = store.read(pid, "step4") or {}
    names = [g["name"] for g in s4.get("ad_groups", [])] or list(existing)
    return [{"name": n, "url": existing.get(n, "")} for n in names]


def run(ctx):
    pid = ctx.project_id
    s5 = store.read(pid, "step5") or {}
    s0 = store.read(pid, "step0") or {}
    groups = _seed_groups(pid, s5)
    base_doc = {"project_id": pid, "step": "step5", "label": store.project_label(pid)}
    keep = {k: s5[k] for k in ("mode", "design_source_url", "custom_domain", "netlify_site_id",
                               "chat", "revision_notes", "plan") if s5.get(k)}
    if ctx.payload.get("plan"):
        if not groups:
            raise Blocked("Landing pages need ad groups from Step 4 first.")
        plan = _plan(ctx, s0, groups, s5.get("plan_note", ""))
        store.publish_step(pid, "step5", {**s5, **base_doc, "ad_groups": groups,
                                          "plan": {"pages": plan, "note": s5.get("plan_note", "")}},
                           row_count=len(plan))
        ctx.need_approval(f"Landing page plan ready: {len(plan)} pages for {len(groups)} ad groups. "
                          "Check it, then press Build.")
        return
    building = s5.get("mode") in BUILD_MODES and (
        ctx.payload.get("build") or ctx.payload.get("retry") or ctx.job["kind"] == "revise_step")
    if not building:
        store.publish_step(pid, "step5", {**base_doc, **keep, **{k: s5[k] for k in s5 if k not in base_doc and k != "ad_groups"},
                                         "ad_groups": groups}, row_count=len(groups))
        ctx.need_approval("Choose how to get your landing pages.")
        return
    if not groups:
        raise Blocked("Landing pages need ad groups from Step 4 first.")
    # Every chat / "Ask for changes" note so far, so a rebuild never drops an earlier change.
    notes = list(s5.get("revision_notes") or [])
    extra = (ctx.payload.get("note") or "").strip()
    if extra and extra not in notes:
        notes.append(extra)
        keep["revision_notes"] = notes
    result = build(ctx, s5, s0, groups, "; ".join(f"({i}) {n}" for i, n in enumerate(notes, 1)) if len(notes) > 1
                   else (notes[0] if notes else ""))
    chat = [dict(m) for m in (s5.get("chat") or [])]
    done = [m for m in chat if m.get("role") == "user" and not m.get("applied")]
    for m in done:
        m["applied"] = True
    if done:
        chat.append({"role": "assistant", "at": time.strftime("%Y-%m-%d %H:%M"),
                     "text": "Done. I rebuilt the landing pages with that change. Have a look at the links above."
                             + (f" Check: {'; '.join(result['warnings'])}" if result["warnings"] else "")})
        keep["chat"] = chat
    store.publish_step(pid, "step5", {**base_doc, **keep, **result}, row_count=len(result["pages"]))
    flagged = f" Check: {'; '.join(result['warnings'])}" if result["warnings"] else ""
    ctx.need_approval(f"{len(result['pages'])} landing pages built, plus index, privacy and terms.{flagged}")


register_step("step5")(run)
