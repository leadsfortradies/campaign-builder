// Step 6 review view - {project_id, step: "step6", label,
// ad_groups: [{name, sitelinks: [{text, description_1, description_2, url}]}],
// callouts: [text, ...], structured_snippets: {header, values: [text, ...]}}.
// Every item (sitelink / callout / snippet value) is excluded/kept as one
// unit - reuses storageKey()/loadExcluded() from review.js.

const SL_LIMITS = { text: 35, description: 25, callout: 25, snippet: 25 };

function sitelinkId(groupName, index) {
  return `sitelink::${groupName}::${index}`;
}
function calloutId(index) {
  return `callout::${index}`;
}
function snippetId(index) {
  return `snippet::${index}`;
}

class SitelinksView {
  constructor({ mountEl, statusEl, countsEl, stepData, onApproved }) {
    this.mountEl = mountEl;
    this.statusEl = statusEl;
    this.countsEl = countsEl;
    this.data = stepData;
    this.onApproved = onApproved;
    this.excluded = loadExcluded(stepData.project_id, stepData.step);
  }

  saveExcluded() {
    try {
      localStorage.setItem(storageKey(this.data.project_id, this.data.step), JSON.stringify([...this.excluded]));
    } catch (e) {
      /* ignore */
    }
  }

  allSitelinks() {
    const items = [];
    for (const group of this.data.ad_groups) {
      group.sitelinks.forEach((sl, index) => items.push({ group: group.name, index, ...sl }));
    }
    return items;
  }

  allCallouts() {
    return (this.data.callouts || []).map((text, index) => ({ text, index }));
  }

  allSnippetValues() {
    return (this.data.structured_snippets?.values || []).map((text, index) => ({ text, index }));
  }

  renderCount(label, text, limit) {
    const len = text.length;
    const span = document.createElement("span");
    span.className = "ac-count" + (len > limit ? " over" : "");
    span.textContent = `${label} ${len}/${limit}`;
    return span;
  }

  renderCard(item) {
    const id = sitelinkId(item.group, item.index);
    const isExcluded = this.excluded.has(id);

    const card = document.createElement("div");
    card.className = "sl-card" + (isExcluded ? " excluded" : "");

    const head = document.createElement("div");
    head.className = "sl-head";

    const textSpan = document.createElement("span");
    textSpan.className = "sl-text";
    textSpan.textContent = item.text;
    head.appendChild(textSpan);
    head.appendChild(this.renderCount("Text", item.text, SL_LIMITS.text));

    const xBtn = document.createElement("button");
    xBtn.className = "x-btn";
    xBtn.textContent = isExcluded ? "↺" : "✕";
    xBtn.title = isExcluded ? "Restore this sitelink" : "Exclude this sitelink";
    xBtn.addEventListener("click", () => this.toggleItem(id));
    head.appendChild(xBtn);

    card.appendChild(head);

    const descs = document.createElement("div");
    descs.className = "sl-descs";
    [item.description_1, item.description_2].forEach((d) => {
      const row = document.createElement("div");
      row.className = "sl-desc-row";
      const t = document.createElement("span");
      t.className = "sl-desc-text";
      t.textContent = d;
      row.appendChild(t);
      row.appendChild(this.renderCount("Desc", d, SL_LIMITS.description));
      descs.appendChild(row);
    });
    card.appendChild(descs);

    const url = document.createElement("div");
    url.className = "sl-url";
    url.textContent = item.url;
    card.appendChild(url);

    return card;
  }

  renderSimpleCard(text, id, limit, excludeTitle) {
    const isExcluded = this.excluded.has(id);

    const card = document.createElement("div");
    card.className = "sl-card" + (isExcluded ? " excluded" : "");

    const head = document.createElement("div");
    head.className = "sl-head";

    const textSpan = document.createElement("span");
    textSpan.className = "sl-text";
    textSpan.textContent = text;
    head.appendChild(textSpan);
    head.appendChild(this.renderCount("Text", text, limit));

    const xBtn = document.createElement("button");
    xBtn.className = "x-btn";
    xBtn.textContent = isExcluded ? "↺" : "✕";
    xBtn.title = isExcluded ? `Restore this ${excludeTitle}` : `Exclude this ${excludeTitle}`;
    xBtn.addEventListener("click", () => this.toggleItem(id));
    head.appendChild(xBtn);

    card.appendChild(head);
    return card;
  }

  renderGroupShell(dotColor, heading, keptCount, totalCount) {
    const group = document.createElement("div");
    group.className = "group";

    const header = document.createElement("div");
    header.className = "group-header";
    header.innerHTML = `
      <span class="dot" style="background:${dotColor}"></span>
      <h2>${heading}</h2>
      <span class="group-count">${keptCount} / ${totalCount} kept</span>
      <span class="chevron">▾</span>
    `;
    header.addEventListener("click", () => group.classList.toggle("collapsed"));
    group.appendChild(header);

    const body = document.createElement("div");
    body.className = "sl-body";
    group.appendChild(body);

    return { group, body };
  }

  render() {
    this.mountEl.innerHTML = "";

    let totalKept = 0;
    let totalAll = 0;

    this.data.ad_groups.forEach((adGroup) => {
      const items = adGroup.sitelinks.map((sl, index) => ({ group: adGroup.name, index, ...sl }));

      let keptInGroup = 0;
      for (const item of items) {
        totalAll++;
        if (!this.excluded.has(sitelinkId(item.group, item.index))) {
          keptInGroup++;
          totalKept++;
        }
      }

      const { group, body } = this.renderGroupShell("#3ddc84", adGroup.name, keptInGroup, items.length);
      for (const item of items) body.appendChild(this.renderCard(item));
      this.mountEl.appendChild(group);
    });

    const callouts = this.allCallouts();
    if (callouts.length) {
      let kept = 0;
      for (const c of callouts) {
        totalAll++;
        if (!this.excluded.has(calloutId(c.index))) {
          kept++;
          totalKept++;
        }
      }
      const { group, body } = this.renderGroupShell("#5b8def", "Callouts (Account-Wide)", kept, callouts.length);
      for (const c of callouts) body.appendChild(this.renderSimpleCard(c.text, calloutId(c.index), SL_LIMITS.callout, "callout"));
      this.mountEl.appendChild(group);
    }

    const snippetValues = this.allSnippetValues();
    if (snippetValues.length) {
      let kept = 0;
      for (const s of snippetValues) {
        totalAll++;
        if (!this.excluded.has(snippetId(s.index))) {
          kept++;
          totalKept++;
        }
      }
      const header = this.data.structured_snippets?.header || "Structured Snippet";
      const { group, body } = this.renderGroupShell("#c77dff", `Structured Snippet — ${header}`, kept, snippetValues.length);
      for (const s of snippetValues) body.appendChild(this.renderSimpleCard(s.text, snippetId(s.index), SL_LIMITS.snippet, "snippet value"));
      this.mountEl.appendChild(group);
    }

    if (this.countsEl) {
      this.countsEl.innerHTML =
        `<span><strong>${totalKept}</strong> kept</span><span><strong>${totalAll - totalKept}</strong> excluded</span><span><strong>${totalAll}</strong> total</span>`;
    }
  }

  toggleItem(id) {
    if (this.excluded.has(id)) {
      this.excluded.delete(id);
    } else {
      this.excluded.add(id);
    }
    this.saveExcluded();
    this.render();
  }

  resetExclusions() {
    this.excluded = new Set();
    this.saveExcluded();
    this.render();
  }

  keptSitelinks() {
    return this.allSitelinks().filter((item) => !this.excluded.has(sitelinkId(item.group, item.index)));
  }

  keptCallouts() {
    return this.allCallouts().filter((c) => !this.excluded.has(calloutId(c.index)));
  }

  keptSnippetValues() {
    return this.allSnippetValues().filter((s) => !this.excluded.has(snippetId(s.index)));
  }

  exportCSV() {
    const header = ["type", "ad_group", "text", "description_1", "description_2", "final_url"];
    const lines = [header.join(",")];
    const csvRow = (vals) =>
      vals
        .map((v) => {
          const s = String(v ?? "");
          const escaped = s.replace(/"/g, '""');
          return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
        })
        .join(",");

    for (const item of this.keptSitelinks()) {
      lines.push(csvRow(["sitelink", item.group, item.text, item.description_1, item.description_2, item.url]));
    }
    for (const c of this.keptCallouts()) {
      lines.push(csvRow(["callout", "", c.text, "", "", ""]));
    }
    const snippetHeader = this.data.structured_snippets?.header || "";
    for (const s of this.keptSnippetValues()) {
      lines.push(csvRow(["snippet", snippetHeader, s.text, "", "", ""]));
    }

    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${this.data.project_id}_${this.data.step}_kept.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  showStatus(msg, ok) {
    if (!this.statusEl) return;
    this.statusEl.textContent = msg;
    this.statusEl.hidden = false;
    this.statusEl.className = `status-msg ${ok ? "ok" : "err"}`;
  }

  async submitApproval(btn, nextLabel) {
    const keptSitelinks = this.keptSitelinks();
    const keptCallouts = this.keptCallouts().map((c) => c.text);
    const keptSnippetValues = this.keptSnippetValues().map((s) => s.text);
    const totalAll =
      this.allSitelinks().length + this.allCallouts().length + this.allSnippetValues().length;
    const totalKept = keptSitelinks.length + keptCallouts.length + keptSnippetValues.length;

    const payload = {
      project_id: this.data.project_id,
      step: this.data.step,
      dataset_label: this.data.label,
      submitted_at: new Date().toISOString(),
      total_kept: totalKept,
      total_excluded: totalAll - totalKept,
      kept_items: keptSitelinks,
      kept_callouts: keptCallouts,
      structured_snippet_header: this.data.structured_snippets?.header || "",
      kept_snippet_values: keptSnippetValues,
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
      this.showStatus(`Submitted ${totalKept} items${nextLabel ? ` — ${nextLabel}` : ""}.`, true);
      btn.textContent = "Submitted ✓";
      if (this.onApproved) this.onApproved();
    } catch (e) {
      this.showStatus("Submission failed — check your connection and try again, or use Export CSV instead.", false);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}
