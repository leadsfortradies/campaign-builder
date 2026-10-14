"""Chat box on the review pages: turn a plain instruction ("remove all the
general builder keywords") into exclude/restore lists for the keyword table."""

from . import llm

SYSTEM = (
    "You help a Google Ads specialist edit a keyword list on screen. They type a plain "
    "instruction such as 'remove all the general builder keywords and only keep the specific "
    "ones like deck builder palmerston north'. Decide which keywords on their list the "
    "instruction removes (exclude) or brings back (restore). Use ONLY keywords copied exactly "
    "from the list. Apply the instruction literally and consistently to every matching keyword. "
    "Return JSON: {\"exclude\": [keywords], \"restore\": [keywords], \"reply\": \"one or two "
    "plain sentences saying what you did\"}. If the instruction isn't about editing this "
    "keyword list, return empty lists and explain in reply."
)


class _Ctx:
    """Just enough of jobs.Ctx for llm.complete_json outside a job."""
    def __init__(self, model):
        self.model = model

    def add_usage(self, tin, tout):
        pass

    def log(self, msg):
        print(f"[chat] {msg}", flush=True)


def suggest(rows, message, excluded, model):
    if not rows:
        return {"exclude": [], "restore": [], "reply": "There's no keyword list on this step to edit."}
    excluded = set(excluded)
    lines = "\n".join(
        f"{r['keyword']} | {r.get('group', '')} | {r.get('avg_monthly_searches', 0)}/mo"
        + (" | EXCLUDED" if r["keyword"] in excluded else "")
        for r in rows
    )
    user = f"Instruction: {message}\n\nKeyword list (keyword | group | volume):\n{lines}"
    out = llm.complete_json(_Ctx(model), SYSTEM, user, max_tokens=16000)
    valid = {r["keyword"] for r in rows}
    pick = lambda k: [x for x in dict.fromkeys(out.get(k) or []) if x in valid]
    return {"exclude": pick("exclude"), "restore": pick("restore"), "reply": str(out.get("reply") or "")}
