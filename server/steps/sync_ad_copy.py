"""Background job "sync_ad_copy": after the user edits ad groups on Step 3
(deletes an ad group, moves keywords, adds a group), bring the ad copy (step4),
the extensions (step6) and the landing page list (step5) in line with it.

Only what changed is touched: deleted ad groups are removed, new ad groups get
fresh copy, ad groups whose keywords changed are rewritten, everything else is
left exactly as it was. The step3.json file is also updated to the approved
rows, because the Google Ads upload reads that file."""

from .. import db, llm
from ..jobs import Blocked, register
from ..notify import notify
from . import link_urls, step4, step6, store


def _sig(kws):
    return sorted(k["keyword"] for k in kws)


def _refresh_snippet(ctx, facts, names, snip):
    user = f"""Business facts: {facts}
Ad groups now running: {names}
Current structured snippet: header "{snip.get('header', '')}", values {snip.get('values', [])}

Update the snippet values so they only list services the ad groups above actually cover.
Return JSON: {{"values": [4 to 8 items, each max 25 chars, Title Case]}}"""
    try:
        out = llm.complete_json(ctx, step6.RULES, user, max_tokens=600)
    except llm.LLMError:
        return snip
    vals = [v for v in out.get("values", []) if isinstance(v, str) and v and len(v) <= 25
            and not step6.BANNED.search(v)]
    return {**snip, "values": vals} if 4 <= len(vals) <= 8 else snip


@register("sync_ad_copy")
def sync(ctx):
    pid = ctx.project_id
    s0 = store.read(pid, "step0") or {}
    s4 = store.read(pid, "step4") or {}
    if not s4.get("ad_groups"):
        raise Blocked("There's no ad copy to update yet.")
    sets = step4.ad_group_sets(pid)
    if not sets:
        raise Blocked("Every ad group in the ad copy campaigns has been deleted. Keep at least one.")
    rows = store.approved_rows(pid, "step3")
    groups = {n: kws for n, (_, _, kws) in sets.items()}

    # Step 8 reads step3.json, so it must reflect the approved edits (original kept once).
    s3 = store.read(pid, "step3")
    if s3:
        if not store.read(pid, "step3_original"):
            store.write(pid, "step3_original", s3)
        store.write(pid, "step3", {**s3, "rows": rows})

    facts = {k: s0[k] for k in step4.FACT_FIELDS if s0.get(k)}
    old = {g["name"]: g for g in s4["ad_groups"]}
    removed = [n for n in old if n not in groups]
    added, rewritten, out = [], [], []
    for name, kws in groups.items():
        kws.sort(key=lambda r: -r["avg_monthly_searches"])
        sig, prev = _sig(kws), old.get(name)
        if prev is None:
            g = step4._write_group(ctx, facts, name, kws, "", None, *sets[name][:2])
            added.append(name)
        elif prev.get("keywords") is not None and prev["keywords"] != sig:
            g = step4._write_group(ctx, facts, name, kws,
                                   "The keywords in this ad group changed; make sure the copy still fits them.", prev,
                                   *sets[name][:2])
            rewritten.append(name)
        else:
            g = prev
        g["keywords"] = sig
        g.setdefault("campaign", sets[name][0])
        g.setdefault("theme", sets[name][1])
        out.append(g)
    items = sum(len(g["headlines_pinned"]) + len(g["headlines_benefit"]) + len(g["descriptions"]) + len(g["paths"])
                for g in out)
    store.publish_step(pid, "step4", {**s4, "ad_groups": out}, row_count=items)

    # Extensions
    s6 = store.read(pid, "step6")
    if s6 and s6.get("ad_groups"):
        by = {g["name"]: g for g in s6["ad_groups"]}
        template = s6["ad_groups"][0]
        new6 = []
        for g in out:
            if g["name"] in by:
                new6.append(by[g["name"]])
                continue
            base = g.get("final_url", "")
            links = []
            for sl in template.get("sitelinks", []):
                anchor = sl.get("url", "").split("#", 1)[1] if "#" in sl.get("url", "") else ""
                url = link_urls._swap_base(f"#{anchor}", base) if base else f"#{anchor}"
                links.append({**sl, "url": url})
            warn = [] if base else ["No landing page URL yet - links point at the anchor only until landing pages are built."]
            new6.append({"name": g["name"], "sitelinks": links, "warnings": warn})
        snip = s6.get("structured_snippets") or {}
        if removed or added:
            snip = _refresh_snippet(ctx, facts, [g["name"] for g in out], snip)
        count = sum(len(g["sitelinks"]) for g in new6) + len(s6.get("callouts", [])) + len(snip.get("values", []))
        store.publish_step(pid, "step6", {**s6, "ad_groups": new6, "structured_snippets": snip}, row_count=count)

    # Landing pages: drop deleted ad groups from the list and the plan; new ones wait for a rebuild.
    s5 = store.read(pid, "step5")
    if s5 and (removed or added):
        urls = {g["name"]: g.get("url", "") for g in s5.get("ad_groups", [])}
        s5["ad_groups"] = [{"name": n, "url": urls.get(n, "")} for n in groups]
        for pg in s5.get("pages", []) + (s5.get("plan") or {}).get("pages", []):
            pg["ad_groups"] = [n for n in pg.get("ad_groups", []) if n in groups]
        if added and s5.get("pages"):
            s5["warnings"] = [w for w in s5.get("warnings", []) if not w.startswith("New ad groups")] + [
                f"New ad groups have no landing page yet ({', '.join(added)}). Rebuild the landing pages."]
        store.write(pid, "step5", s5)

    bits = []
    if removed:
        bits.append(f"removed {len(removed)} ad group{'s' if len(removed) != 1 else ''}")
    if added:
        bits.append(f"wrote copy for {len(added)} new")
    if rewritten:
        bits.append(f"rewrote {len(rewritten)} with changed keywords")
    msg = "Ad copy and extensions updated: " + (", ".join(bits) or "no copy changes needed") + "."
    ctx.log(msg)
    db.log_event("adcopy_synced", pid, "step4", msg)
    ctx.need_approval(msg + " Review the ad copy and extensions, then approve.")
