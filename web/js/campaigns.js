// "Campaigns to Build" step: pick which campaigns get built, and whether
// Priority 1 and 2 are combined. Data: {project_id, step: "campaigns", label,
// counts: {campaign: n}, merged_name, default: {campaigns, merge_bof}}.

const CAMPAIGN_INFO = [
  ["BOF - Priority 1", "Highest-intent searches (Tier A/B). Launches first."],
  ["BOF - Priority 2", "Still buying intent, lower volume or broader terms."],
  ["Price Discovery", "People asking about cost / price. Kept separate so they don't eat the lead budget."],
];

class CampaignsView {
  constructor({ mountEl, statusEl, countsEl, stepData, onApproved }) {
    this.mountEl = mountEl;
    this.statusEl = statusEl;
    this.countsEl = countsEl;
    this.data = stepData;
    this.onApproved = onApproved;
    const d = stepData.default || {};
    this.picked = new Set(d.campaigns || CAMPAIGN_INFO.map((c) => c[0]));
    this.merge = !!d.merge_bof;
  }

  render() {
    const counts = this.data.counts || {};
    const box = document.createElement("div");
    box.className = "group";
    box.style.padding = "18px";
    box.innerHTML = "<h2 style='margin-top:0'>Which campaigns do you want built?</h2>";
    for (const [name, blurb] of CAMPAIGN_INFO) {
      const label = document.createElement("label");
      label.style.cssText = "display:block;margin:12px 0;cursor:pointer";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = this.picked.has(name);
      cb.onchange = () => {
        cb.checked ? this.picked.add(name) : this.picked.delete(name);
        this.render();
      };
      label.append(cb, ` ${name} (${counts[name] || 0} keywords) `);
      const small = document.createElement("div");
      small.className = "note";
      small.style.marginLeft = "22px";
      small.textContent = blurb;
      label.appendChild(small);
      box.appendChild(label);
    }
    const bothBof = this.picked.has("BOF - Priority 1") && this.picked.has("BOF - Priority 2");
    if (!bothBof) this.merge = false;
    const mlabel = document.createElement("label");
    mlabel.style.cssText = "display:block;margin:18px 0 4px;cursor:pointer;" + (bothBof ? "" : "opacity:.45");
    const mcb = document.createElement("input");
    mcb.type = "checkbox";
    mcb.checked = this.merge;
    mcb.disabled = !bothBof;
    mcb.onchange = () => { this.merge = mcb.checked; };
    mlabel.append(mcb, ` Combine Priority 1 and Priority 2 into a single campaign (“${this.data.merged_name || "BOF - Priority 1 & 2"}”)`);
    box.appendChild(mlabel);
    this.mountEl.innerHTML = "";
    this.mountEl.appendChild(box);
    if (this.countsEl) this.countsEl.innerHTML = `<span><strong>${this.picked.size}</strong> campaigns chosen</span>`;
  }

  showStatus(msg, ok) {
    this.statusEl.textContent = msg;
    this.statusEl.hidden = false;
    this.statusEl.className = `status-msg ${ok ? "ok" : "err"}`;
  }

  async submitApproval(btn) {
    if (!this.picked.size) {
      this.showStatus("Pick at least one campaign.", false);
      return;
    }
    const campaigns = CAMPAIGN_INFO.map((c) => c[0]).filter((c) => this.picked.has(c));
    btn.disabled = true;
    try {
      const res = await fetch("/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: this.data.project_id,
          step: "campaigns",
          submitted_at: new Date().toISOString(),
          total_kept: campaigns.length,
          selection: { campaigns, merge_bof: this.merge },
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.showStatus("Saved - building the ad groups now.", true);
      btn.textContent = "Submitted ✓";
      if (this.onApproved) this.onApproved();
    } catch (e) {
      this.showStatus("Couldn't save that - try again.", false);
      btn.disabled = false;
    }
  }
}
