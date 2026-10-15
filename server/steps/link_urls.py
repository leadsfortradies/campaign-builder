"""Background step: once landing pages (job key "step5") are approved, copy each
ad group's landing page URL into the ad copy's final URL (step4.json) and into
that ad group's sitelinks (step6.json, keeping each link's #anchor). No Claude
call, no review - it only fills in links the user already approved."""

from .. import db
from ..jobs import register
from ..notify import notify
from . import store


def _key(name):
    return " ".join(str(name).lower().split())


def _swap_base(url, base):
    anchor = url.split("#", 1)[1] if "#" in url else ""
    return f"{base.rstrip('/')}#{anchor}" if anchor else base


@register("link_landing_pages")
def link_landing_pages(ctx):
    pid = ctx.project_id
    try:
        pages = {_key(g["name"]): g["url"] for g in (store.read(pid, "step5") or {}).get("ad_groups", [])
                 if g.get("url")}
        if not pages:
            ctx.log("No landing page URLs in Step 6 - nothing to add.")
            return
        changed_ad, changed_sl, missing = 0, 0, []

        s4 = store.read(pid, "step4")
        if s4:
            for g in s4.get("ad_groups", []):
                url = pages.get(_key(g["name"]))
                if not url:
                    missing.append(g["name"])
                elif g.get("final_url") != url:
                    g["final_url"] = url
                    changed_ad += 1
            store.write(pid, "step4", s4)

        s6 = store.read(pid, "step6")
        if s6:
            for g in s6.get("ad_groups", []):
                url = pages.get(_key(g["name"]))
                if not url:
                    continue
                for sl in g.get("sitelinks", []):
                    new = _swap_base(sl.get("url", ""), url)
                    if sl.get("url") != new:
                        sl["url"] = new
                        changed_sl += 1
                g["warnings"] = [w for w in g.get("warnings", []) if not w.startswith("No landing page URL")]
            store.write(pid, "step6", s6)

        msg = f"Landing page links added: {changed_ad} ad groups, {changed_sl} sitelinks."
        if missing:
            msg += f" No landing page found for: {', '.join(missing)}."
        ctx.log(msg)
        db.log_event("links_added", pid, "step5", msg)
        notify(f"Links added: {pid}", msg, f"/project.html?id={pid}&step=step4")
    finally:
        # The job runs under the landing pages step; it must stay approved.
        ctx.set_step(status="approved")
