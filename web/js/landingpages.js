// Landing pages view (step key "step5", shown as Step 6) -
// {project_id, step, label, mode, design_source_url, custom_domain,
//  ad_groups: [{name, url}], pages: [{slug, title, url, ad_groups}], index_url,
//  privacy_url, terms_url, repo_url, dns_note, warnings}. Three options:
//   1 "build_template": the app builds all pages from the LFT site template,
//     plus privacy, terms and index from the template.
//   2 "build_designed": same pages, restyled with the client's own logo, fonts
//     and colours read from their website; privacy/terms copied from that site.
//   3 "urls": one text input per ad group for existing landing page links.
// Build options start a background job via /api/landing/start; the finished
// pages come back in this same data file for review and approval.
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
    if (!raw) return { mode: normMode(data.mode), urls: {}, designUrl: data.design_source_url || "", customDomain: data.custom_domain || "" };
    const parsed = JSON.parse(raw);
    return {
      mode: normMode(parsed.mode || data.mode),
      urls: parsed.urls || {},
      designUrl: parsed.designUrl != null ? parsed.designUrl : data.design_source_url || "",
      customDomain: parsed.customDomain != null ? parsed.customDomain : data.custom_domain || "",
    };
  } catch (e) {
    return { mode: normMode(data.mode), urls: {}, designUrl: data.design_source_url || "", customDomain: data.custom_domain || "" };
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
      ["build_template", "1. Build from scratch", "All landing pages, privacy, terms and index from the LFT template."],
      ["build_designed", "2. Build with the client's branding", "Same template pages, using the logo, fonts and colours from the client's website."],
      ["urls", "3. I already have the links", "Paste a landing page link for each ad group."],
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
    } else if (this.draft.mode === "build_template" || this.draft.mode === "build_designed") {
      this.renderBuild();
    } else {
      const note = document.createElement("div");
      note.className = "skip-note";
      note.textContent = "Pick an option above to get started.";
      this.mountEl.appendChild(note);
    }

    this.updateCounts();
  }

  renderBuild() {
    const designed = this.draft.mode === "build_designed";
    const built = this.data.pages && this.data.pages.length && this.data.mode === this.draft.mode;
    const box = document.createElement("div");
    box.className = "lp-build";
    if (built) {
      const d = this.data;
      // Pages built before preview links used Netlify: show the Netlify address until DNS is confirmed.
      // Two sets of links: the Netlify address (works now) and the final domain (works once DNS is connected).
      const nm = (d.dns_note || "").match(/at ([\w.-]+\.netlify\.app)/);
      const nBase = (d.netlify_base || (/\.netlify\.app/.test(d.preview_base || "") ? d.preview_base : "")
        || (nm ? "https://" + nm[1] : "") || d.preview_base || "").replace(/\/$/, "");
      const cBase = (d.custom_base || (d.custom_domain ? "https://" + d.custom_domain : "")).replace(/\/$/, "");
      const pathOf = (u) => (u || "").replace(/^https?:\/\/[^/]+/, "");
      const linkTo = (base, u, t) => `<a href="${base}${pathOf(u)}" target="_blank" rel="noopener">${t}</a>`;
      const set = (base) => {
        const rows = d.pages
          .map((p) => `<li><strong>${linkTo(base, p.url, p.title || p.name)}</strong><br><span class="muted">${p.ad_groups.join(", ")}</span></li>`)
          .join("");
        const extra = [
          d.index_url ? linkTo(base, d.index_url, "Index") : "",
          d.privacy_url ? linkTo(base, d.privacy_url, "Privacy") : "",
          d.terms_url ? linkTo(base, d.terms_url, "Terms") : "",
        ].filter(Boolean).join(" · ");
        return `<ul class="lp-pages">${rows}</ul><p>${extra}${d.repo_url ? (extra ? " · " : "") + `<a href="${d.repo_url}" target="_blank" rel="noopener">GitHub repo</a>` : ""}</p>`;
      };
      const netlifySet = `<h3>Netlify links <span class="muted">(live now)</span></h3>${set(nBase)}`;
      const finalSet = cBase
        ? `<h3>Final domain links <span class="muted">(${d.domain_connected ? "live" : "work once DNS is connected"})</span></h3>${set(cBase)}`
        : "";
      box.innerHTML = `
        <div class="group-header"><span class="dot" style="background:#3ddc84"></span><h2>Landing pages built</h2></div>
        ${netlifySet}
        ${finalSet}
        <p class="lp-actions">
          <button type="button" class="btn lp-rebuild">Rebuild landing pages</button>
        </p>
        ${cBase && !d.domain_connected ? `<div class="skip-note"><strong>Is the final domain connected?</strong>
          Ad copy and sitelinks use the final domain links (${cBase.replace("https://", "")}), never the Netlify ones.
          ${d.dns_note || ""} No campaign is uploaded until you confirm this.
          <p><button type="button" class="btn lp-dns-done">Yes, the final domain is connected</button></p></div>` : ""}
        ${d.domain_connected && d.custom_base ? `<p class="muted">Final domain confirmed as connected (${d.custom_base.replace("https://", "")}). Campaigns can be uploaded.</p>` : ""}
        ${(d.warnings || []).map((w) => `<p class="skip-note"><strong>Check:</strong> ${w}</p>`).join("")}
        <p class="muted">Review the pages, then approve. Approving adds each ad group's link to its ad copy and sitelinks.
        To change something, use Request changes and describe it.</p>`;
      box.appendChild(this.chatPanel(d));
      const rebuildBtn = box.querySelector(".lp-rebuild");
      rebuildBtn.addEventListener("click", async () => {
        if (!confirm("Rebuild all landing pages? This replaces what is currently live on the same Netlify site.")) return;
        rebuildBtn.disabled = true;
        rebuildBtn.textContent = "Starting…";
        try {
          const res = await fetch("/api/landing/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              project_id: d.project_id,
              mode: d.mode,
              design_source_url: d.design_source_url || "",
              custom_domain: d.custom_domain || "",
            }),
          });
          if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
          location.reload();
        } catch (e) {
          rebuildBtn.disabled = false;
          rebuildBtn.textContent = "Rebuild landing pages";
          this.showStatus(`Couldn't start the rebuild: ${e.message}`, false);
        }
      });
      const dnsBtn = box.querySelector(".lp-dns-done");
      if (dnsBtn) {
        dnsBtn.addEventListener("click", async () => {
          dnsBtn.disabled = true;
          dnsBtn.textContent = "Switching links…";
          try {
            const res = await fetch("/api/landing/domain-connected", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ project_id: this.data.project_id }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            location.reload();
          } catch (e) {
            dnsBtn.disabled = false;
            dnsBtn.textContent = "Yes, the final domain is connected";
            this.showStatus("Couldn't switch the links. Try again.", false);
          }
        });
      }
      this.mountEl.appendChild(box);
      return;
    }
    const field = (label, key, ph) => {
      const row = document.createElement("div");
      row.className = "lp-row";
      row.innerHTML = `<span class="lp-label">${label}</span>`;
      const input = document.createElement("input");
      input.type = "text";
      input.className = "lp-input";
      input.placeholder = ph;
      input.value = this.draft[key] || "";
      input.addEventListener("input", () => {
        this.draft[key] = input.value;
        this.saveDraft();
      });
      row.appendChild(input);
      box.appendChild(row);
    };
    if (designed) field("Client's website", "designUrl", "https://clientsite.co.nz");
    field("Live address (optional)", "customDomain", designed ? "quotes.clientsite.co.nz" : "www.clientsite.co.nz");
    const note = document.createElement("div");
    note.className = "skip-note";
    note.innerHTML = designed
      ? "Builds the landing pages on the LFT template with this client's logo, fonts and colours, and copies their privacy policy and terms from their site. You set up the subdomain DNS yourself; leave the address blank to use the temporary Netlify link."
      : "Builds all landing pages, privacy, terms and index from the LFT template, with the client's logo and photos. Leave the address blank to use the temporary Netlify link.";
    box.appendChild(note);
    const btn = document.createElement("button");
    btn.className = "primary";
    btn.textContent = "Build landing pages";
    btn.addEventListener("click", () => this.startBuild(btn));
    box.appendChild(btn);
    this.mountEl.appendChild(box);
  }

  // Chat for revisions: each message is saved with the project and rebuilds the
  // pages with every note so far applied (server: POST /api/landing/revise).
  chatPanel(d) {
    const wrap = document.createElement("div");
    wrap.className = "lp-chat";
    const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const msgs = (d.chat || [])
      .map((m) => `<div class="lp-msg ${m.role}"><span>${esc(m.text)}</span>${
        m.role === "user" && !m.applied ? '<em class="muted"> (not applied yet)</em>' : ""}</div>`)
      .join("");
    wrap.innerHTML = `
      <h3>Ask for changes</h3>
      <div class="lp-chat-log">${msgs || '<p class="muted">Nothing asked for yet.</p>'}</div>
      <form class="lp-chat-form">
        <input type="text" class="lp-input" autocomplete="off"
          placeholder="e.g. Change the heading on the fencing page, say we cover Feilding too, lead with the driveway photos">
        <button type="submit" class="primary">Send</button>
      </form>
      <p class="muted">Each message rebuilds the pages with all your changes so far (a few minutes). Good for wording,
      services, areas, page grouping and which photos lead. For a new logo or photos, update Business info and use Rebuild.</p>`;
    const log = wrap.querySelector(".lp-chat-log");
    log.scrollTop = log.scrollHeight;
    wrap.querySelector("form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const input = wrap.querySelector("input");
      const btn = wrap.querySelector("button");
      const message = input.value.trim();
      if (!message) return;
      btn.disabled = true;
      btn.textContent = "Sending…";
      try {
        const res = await fetch("/api/landing/revise", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: d.project_id, message }),
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        location.reload();
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "Send";
        this.showStatus(`Couldn't send that: ${e.message}`, false);
      }
    });
    return wrap;
  }

  async startBuild(btn) {
    if (this.draft.mode === "build_designed" && !(this.draft.designUrl || "").trim()) {
      this.showStatus("Add the client's website link first.", false);
      return;
    }
    btn.disabled = true;
    btn.textContent = "Starting…";
    try {
      const res = await fetch("/api/landing/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: this.data.project_id,
          mode: this.draft.mode,
          design_source_url: (this.draft.designUrl || "").trim(),
          custom_domain: (this.draft.customDomain || "").trim(),
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
      location.reload();
    } catch (e) {
      this.showStatus(`Couldn't start the build: ${e.message}`, false);
      btn.disabled = false;
      btn.textContent = "Build landing pages";
    }
  }

  updateCounts() {
    if (!this.countsEl) return;
    if (this.draft.mode !== "urls") {
      this.countsEl.innerHTML = this.data.pages ? `<span><strong>${this.data.pages.length}</strong> pages built</span>` : "";
      return;
    }
    const total = this.data.ad_groups.length;
    const filled = this.data.ad_groups.filter((g) => this.urlFor(g).trim() !== "").length;
    this.countsEl.innerHTML = `<span><strong>${filled}</strong> filled</span><span><strong>${total}</strong> ad groups</span>`;
  }

  resetExclusions() {
    this.draft = { mode: normMode(this.data.mode), urls: {}, designUrl: this.data.design_source_url || "", customDomain: this.data.custom_domain || "" };
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
    } else if (!(this.data.pages && this.data.pages.length && this.data.mode === this.draft.mode)) {
      this.showStatus("Build the landing pages first, then approve them.", false);
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
