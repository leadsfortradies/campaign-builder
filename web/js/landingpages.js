// Step 5 view - {project_id, step: "step5", label, mode: "urls"|"build_site"|null,
// design_source_url, ad_groups: [{name, url}]}. Three modes, chosen at the top:
//   - "build_template": Claude builds new landing pages from the site template.
//   - "urls": one text input per ad group for its existing landing page URL.
//   - "build_designed": Claude builds landing pages on the site template's
//     layout using the design system (logo, fonts, colours) of an existing
//     site, whose link is entered here (design_source_url). Managed ads.
// Mode choice + in-progress URL edits are drafted to localStorage (same
// pattern as loadExcluded() in review.js) until "Approve this step" submits
// them for real.

function landingPagesDraftKey(projectId, step) {
  return `lft-lp-draft::${projectId}::${step}`;
}

function normMode(m) {
  return m === "build_site" ? "build_template" : m || null;
}

function loadLandingPagesDraft(projectId, step, data) {
  try {
    const raw = localStorage.getItem(landingPagesDraftKey(projectId, step));
    if (!raw) return { mode: normMode(data.mode), urls: {}, designUrl: data.design_source_url || "" };
    const parsed = JSON.parse(raw);
    return {
      mode: normMode(parsed.mode || data.mode),
      urls: parsed.urls || {},
      designUrl: parsed.designUrl != null ? parsed.designUrl : data.design_source_url || "",
    };
  } catch (e) {
    return { mode: normMode(data.mode), urls: {}, designUrl: data.design_source_url || "" };
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

    const options = [
      ["build_template", "Build new landing pages from scratch", "Claude builds them using the site template."],
      ["urls", "Landing pages already exist", "Paste a landing page link for each ad group."],
      ["build_designed", "Build with an existing site's design", "Site template layout, styled to match a client's existing site. Managed ads."],
    ];
    for (const [value, title, blurb] of options) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "lp-mode-card" + (this.draft.mode === value ? " selected" : "");
      card.innerHTML = `<strong>${title}</strong><span>${blurb}</span>`;
      card.addEventListener("click", () => this.setMode(value));
      modeRow.appendChild(card);
    }

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
    } else if (this.draft.mode === "build_template") {
      const note = document.createElement("div");
      note.className = "skip-note";
      note.innerHTML = `<strong>Approve this step and tell Claude in chat.</strong> It will build the landing pages from the site template and fill in the URLs once they're live.`;
      this.mountEl.appendChild(note);
    } else if (this.draft.mode === "build_designed") {
      const wrap = document.createElement("div");
      wrap.className = "lp-row";
      const label = document.createElement("span");
      label.className = "lp-label";
      label.textContent = "Existing site link";
      wrap.appendChild(label);
      const input = document.createElement("input");
      input.type = "url";
      input.className = "lp-input";
      input.placeholder = "https://clientsite.co.nz";
      input.value = this.draft.designUrl || "";
      input.addEventListener("input", () => {
        this.draft.designUrl = input.value;
        this.saveDraft();
      });
      wrap.appendChild(input);
      this.mountEl.appendChild(wrap);
      const note = document.createElement("div");
      note.className = "skip-note";
      note.innerHTML = `<strong>Approve this step and tell Claude in chat.</strong> It will pull the logo, fonts and colours from that site, build the landing pages on the site template layout (new Netlify project + GitHub repo, subdomain), and fill in the URLs once live.`;
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
    this.draft = { mode: normMode(this.data.mode), urls: {}, designUrl: this.data.design_source_url || "" };
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
    } else if (this.draft.mode === "build_designed" && !(this.draft.designUrl || "").trim()) {
      this.showStatus("Add the existing site link first.", false);
      return;
    }

    const adGroups = this.data.ad_groups.map((g) => ({ name: g.name, url: this.urlFor(g) }));
    const payload = {
      project_id: this.data.project_id,
      step: this.data.step,
      dataset_label: this.data.label,
      submitted_at: new Date().toISOString(),
      mode: this.draft.mode,
      design_source_url: this.draft.mode === "build_designed" ? this.draft.designUrl.trim() : null,
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
