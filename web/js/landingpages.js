// Step 5 view - {project_id, step: "step5", label, mode: "urls"|"build_site"|null,
// ad_groups: [{name, url}]}. Two modes, chosen with a toggle at the top:
//   - "urls": one text input per ad group for its landing page URL.
//   - "build_site": placeholder only - button is disabled, nothing wired up
//     behind it yet.
// Mode choice + in-progress URL edits are drafted to localStorage (same
// pattern as loadExcluded() in review.js) until "Approve this step" submits
// them for real.

function landingPagesDraftKey(projectId, step) {
  return `lft-lp-draft::${projectId}::${step}`;
}

function loadLandingPagesDraft(projectId, step, data) {
  try {
    const raw = localStorage.getItem(landingPagesDraftKey(projectId, step));
    if (!raw) return { mode: data.mode || null, urls: {} };
    const parsed = JSON.parse(raw);
    return { mode: parsed.mode || data.mode || null, urls: parsed.urls || {} };
  } catch (e) {
    return { mode: data.mode || null, urls: {} };
  }
}

class LandingPagesView {
  constructor({ mountEl, statusEl, countsEl, stepData, onApproved }) {
    this.mountEl = mountEl;
    this.statusEl = statusEl;
    this.countsEl = countsEl;
    this.data = stepData;
    this.onApproved = onApproved;
    this.draft = loadLandingPagesDraft(stepData.project_id, stepData.step, stepData);
  }

  saveDraft() {
    try {
      localStorage.setItem(
        landingPagesDraftKey(this.data.project_id, this.data.step),
        JSON.stringify(this.draft)
      );
    } catch (e) {
      /* ignore */
    }
  }

  urlFor(adGroup) {
    if (adGroup.name in this.draft.urls) return this.draft.urls[adGroup.name];
    return adGroup.url || "";
  }

  setMode(mode) {
    this.draft.mode = mode;
    this.saveDraft();
    this.render();
  }

  render() {
    this.mountEl.innerHTML = "";

    const modeRow = document.createElement("div");
    modeRow.className = "lp-mode-row";

    const urlsCard = document.createElement("button");
    urlsCard.type = "button";
    urlsCard.className = "lp-mode-card" + (this.draft.mode === "urls" ? " selected" : "");
    urlsCard.innerHTML = `<strong>I'll provide the URLs</strong><span>Paste a landing page link for each ad group below.</span>`;
    urlsCard.addEventListener("click", () => this.setMode("urls"));
    modeRow.appendChild(urlsCard);

    const buildCard = document.createElement("button");
    buildCard.type = "button";
    buildCard.className = "lp-mode-card" + (this.draft.mode === "build_site" ? " selected" : "");
    buildCard.innerHTML = `<strong>Build me a site + landing pages</strong><span class="lp-soon">Coming soon - not built yet</span>`;
    buildCard.disabled = true;
    modeRow.appendChild(buildCard);

    this.mountEl.appendChild(modeRow);

    if (this.draft.mode === "urls") {
      const group = document.createElement("div");
      group.className = "group";

      const header = document.createElement("div");
      header.className = "group-header";
      header.innerHTML = `
        <span class="dot" style="background:#3ddc84"></span>
        <h2>Landing page per ad group</h2>
        <span class="group-count"></span>
      `;
      group.appendChild(header);

      const body = document.createElement("div");
      body.className = "lp-body";

      for (const adGroup of this.data.ad_groups) {
        const row = document.createElement("div");
        row.className = "lp-row";

        const label = document.createElement("span");
        label.className = "lp-label";
        label.textContent = adGroup.name;
        row.appendChild(label);

        const input = document.createElement("input");
        input.type = "url";
        input.className = "lp-input";
        input.placeholder = "https://example.co.nz/service-page";
        input.value = this.urlFor(adGroup);
        input.addEventListener("input", () => {
          this.draft.urls[adGroup.name] = input.value;
          this.saveDraft();
          this.updateCounts();
        });
        row.appendChild(input);

        body.appendChild(row);
      }

      group.appendChild(body);
      this.mountEl.appendChild(group);
    } else if (this.draft.mode === "build_site") {
      const note = document.createElement("div");
      note.className = "skip-note";
      note.innerHTML = `<strong>Not built yet.</strong> Site + landing page creation isn't implemented - tell Claude in chat and it'll either build this out or switch you back to providing URLs.`;
      this.mountEl.appendChild(note);
    } else {
      const note = document.createElement("div");
      note.className = "skip-note";
      note.textContent = "Pick an option above to get started.";
      this.mountEl.appendChild(note);
    }

    this.updateCounts();
  }

  updateCounts() {
    if (!this.countsEl) return;
    if (this.draft.mode !== "urls") {
      this.countsEl.innerHTML = "";
      return;
    }
    const total = this.data.ad_groups.length;
    const filled = this.data.ad_groups.filter((g) => this.urlFor(g).trim() !== "").length;
    this.countsEl.innerHTML = `<span><strong>${filled}</strong> filled</span><span><strong>${total}</strong> ad groups</span>`;
  }

  resetExclusions() {
    this.draft = { mode: this.data.mode || null, urls: {} };
    this.saveDraft();
    this.render();
  }

  showStatus(msg, ok) {
    if (!this.statusEl) return;
    this.statusEl.textContent = msg;
    this.statusEl.hidden = false;
    this.statusEl.className = `status-msg ${ok ? "ok" : "err"}`;
  }

  exportCSV() {
    const header = ["ad_group", "url"];
    const lines = [header.join(",")];
    for (const adGroup of this.data.ad_groups) {
      const vals = [adGroup.name, this.urlFor(adGroup)].map((v) => {
        const s = String(v).replace(/"/g, '""');
        return /[",\n]/.test(s) ? `"${s}"` : s;
      });
      lines.push(vals.join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${this.data.project_id}_${this.data.step}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async submitApproval(btn, nextLabel) {
    if (this.draft.mode === "urls") {
      const missing = this.data.ad_groups.filter((g) => this.urlFor(g).trim() === "");
      if (missing.length) {
        this.showStatus(`Add a URL for every ad group first - missing: ${missing.map((g) => g.name).join(", ")}.`, false);
        return;
      }
    } else if (!this.draft.mode) {
      this.showStatus("Pick an option above first.", false);
      return;
    }

    const adGroups = this.data.ad_groups.map((g) => ({ name: g.name, url: this.urlFor(g) }));
    const payload = {
      project_id: this.data.project_id,
      step: this.data.step,
      dataset_label: this.data.label,
      submitted_at: new Date().toISOString(),
      mode: this.draft.mode,
      ad_groups: adGroups,
    };

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Submitting…";
    try {
      const res = await fetch("/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.showStatus(`Submitted${nextLabel ? ` — ${nextLabel}` : ""}.`, true);
      btn.textContent = "Submitted ✓";
      if (this.onApproved) this.onApproved();
    } catch (e) {
      this.showStatus("Submission failed — check your connection and try again, or use Export CSV instead.", false);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}
