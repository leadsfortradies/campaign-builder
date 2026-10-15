"""Per-project Claude API cost, from the tokens recorded on every call."""

from . import config, db, jobs


def _usd(model, tin, tout):
    pr = config.MODEL_PRICES.get(model)
    if not pr:
        return None
    return tin / 1e6 * pr["input"] + tout / 1e6 * pr["output"]


def project_cost(project_id):
    rows = [dict(r) for r in db.query(
        "SELECT step, model, input_tokens AS i, output_tokens AS o FROM usage WHERE project_id=?", (project_id,))]
    # Jobs that ran before per-call tracking existed only have totals on the job row.
    rows += [dict(r) for r in db.query(
        "SELECT step, model, input_tokens AS i, output_tokens AS o FROM jobs WHERE project_id=? "
        "AND input_tokens+output_tokens>0 AND id NOT IN (SELECT job_id FROM usage WHERE job_id IS NOT NULL)",
        (project_id,))]
    total, by_step, by_model, unpriced = 0.0, {}, {}, set()
    tin = tout = 0
    for r in rows:
        usd = _usd(r["model"], r["i"], r["o"])
        if usd is None:
            unpriced.add(r["model"])
            usd = 0.0
        total += usd
        tin += r["i"]
        tout += r["o"]
        s = by_step.setdefault(r["step"], {"usd": 0.0, "tokens": 0})
        s["usd"] += usd
        s["tokens"] += r["i"] + r["o"]
        m = by_model.setdefault(r["model"], {"usd": 0.0, "tokens": 0})
        m["usd"] += usd
        m["tokens"] += r["i"] + r["o"]
    return {"project_id": project_id, "total_usd": round(total, 4), "input_tokens": tin, "output_tokens": tout,
            "by_step": by_step, "by_model": by_model, "unpriced_models": sorted(unpriced),
            "token_cap": jobs.PROJECT_TOKEN_CAP, "tokens_used": tin + tout, "estimate": True}
