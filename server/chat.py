"""Chat box on the review pages: turn a plain instruction ("remove all the
general builder keywords") into exclude/restore lists for the keyword table."""

from . import llm

SYSTEM = (
    "You help a Google Ads specialist edit a keyword list on screen. They type a plain "
    "instruction such as 'remove all the general builder keywords and only keep the specific "
    "ones like deck builder palmerston north'. Decide which keywords on their list the "
    "instruction removes (exclude), brings back (restore), or moves to a different ad group "
    "(move). Use ONLY keywords copied exactly from the list. Apply the instruction literally "
    "and consistently to every matching keyword. Groups on the list look like "
    "'<Campaign> — <Ad Group>'. To move keywords, give the plain ad group name (Title Case, "
    "no campaign name, no location): an existing one, or a NEW one when they ask to split "
    "keywords out into their own ad group (e.g. 'Pool Fence Installation'). Each moved keyword "
    "stays in its own campaign. Moves only apply when groups have that '<Campaign> — <Ad Group>' "
    "form. Return JSON: {\"exclude\": [keywords], \"restore\": [keywords], \"move\": "
    "[{\"keyword\": \"...\", \"ad_group\": \"...\"}], \"reply\": \"one or two plain "
    "sentences saying what you did\"}. If the instruction isn't about editing this keyword "
    "list, return empty lists and explain in reply."
)


class _Ctx:
    """Just enough of jobs.Ctx for llm.complete_json outside a job."""
    def __init__(self, model):
        self.model = model

    def add_usage(self, tin, tout):
        pass

    def log(self, msg):
        print(f"[chat] {msg}", flush=True)


def suggest(rows, message, excluded, model, regrouped=None):
    if not rows:
        return {"exclude": [], "restore": [], "reply": "There's no keyword list on this step to edit."}
    excluded = set(excluded)
    regrouped = {k: v for k, v in (regrouped or {}).items() if isinstance(v, str)}
    group_of = {r["keyword"]: regrouped.get(r["keyword"], r.get("group", "")) for r in rows}
    lines = "\n".join(
        f"{r['keyword']} | {group_of[r['keyword']]} | {r.get('avg_monthly_searches', 0)}/mo"
        + (" | EXCLUDED" if r["keyword"] in excluded else "")
        for r in rows
    )
    user = f"Instruction: {message}\n\nKeyword list (keyword | group | volume):\n{lines}"
    out = llm.complete_json(_Ctx(model), SYSTEM, user, max_tokens=16000)
    valid = {r["keyword"] for r in rows}
    pick = lambda k: [x for x in dict.fromkeys(out.get(k) or []) if x in valid]
    moves = {}
    for m in out.get("move") or []:
        if not isinstance(m, dict):
            continue
        kw, name = m.get("keyword"), str(m.get("ad_group") or "").strip()
        current = group_of.get(kw, "")
        if kw in valid and name and " — " in current:
            name = name.split(" — ")[-1].strip()
            moves[kw] = current.split(" — ", 1)[0] + " — " + name
    return {"exclude": pick("exclude"), "restore": pick("restore"),
            "move": [{"keyword": k, "group": g} for k, g in moves.items() if g != group_of[k]],
            "reply": str(out.get("reply") or "")}
