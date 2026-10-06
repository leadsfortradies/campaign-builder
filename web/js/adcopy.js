// Ad-copy review view for Step 4 - {project_id, step, label, ad_groups:
// [{name, headlines_pinned, headlines_benefit, descriptions, paths}]}.
// Reuses storageKey()/loadExcluded() from review.js (same global scope) so
// exclusions persist the same way Step 1/3 do, just keyed by item id instead
// of keyword text.

const FIELD_LIMITS = { headline: 30, description: 90, path: 15 };

function adCopyItemId(groupName, kind, text) {
  return `${groupName}::${kind}::${text}`;
}

class AdCopyView {
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

  allItems() {
    const items = [];
    for (const group of this.data.ad_groups) {
      group.headlines_pinned.forEach((text) => items.push({ group: group.name, kind: "headline", pinned: true, text }));
      group.headlines_benefit.forEach((text) => items.push({ group: group.name, kind: "headline", pinned: false, text }));
      group.descriptions.forEach((text) => items.push({ group: group.name, kind: "description", pinned: false, text }));
      group.paths.forEach((text) => items.push({ group: group.name, kind: "path", pinned: false, text }));
    }
    return items;
  }

  renderChip(item) {
    const id = adCopyItemId(item.group, item.kind, item.text);
    const isExcluded = this.excluded.has(id);
    const limit = FIELD_LIMITS[item.kind];
    const len = item.text.length;

    const row = document.createElement("div");
    row.className = "ac-chip" + (isExcluded ? " excluded" : "") + (item.pinned ? " pinned" : "");

    const textSpan = document.createElement("span");
    textSpan.className = "ac-text";
    textSpan.textContent = item.text;
    row.appendChild(textSpan);

    if (item.pinned) {
      const pin = document.createElement("span");
      pin.className = "ac-pin";
      pin.textContent = "PIN 1";
      row.appendChild(pin);
    }

    const count = document.createElement("span");
    count.className = "ac-count" + (len > limit ? " over" : "");
    count.textContent = `${len}/${limit}`;
    row.appendChild(count);

    const xBtn = document.createElement("button");
    xBtn.className = "x-btn";
    xBtn.textContent = isExcluded ? "↺" : "✕";
    xBtn.title = isExcluded ? "Restore this line" : "Exclude this line";
    xBtn.addEventListener("click", () => this.toggleItem(id));
    row.appendChild(xBtn);

    return row;
  }

  renderSection(title, items) {
    const section = document.createElement("div");
    section.className = "ac-section";
    const h3 = document.createElement("h3");
    h3.textContent = title;
    section.appendChild(h3);
    for (const item of items) section.appendChild(this.renderChip(item));
    return section;
  }

  render() {
    this.mountEl.innerHTML = "";

    let totalKept = 0;
    let totalAll = 0;

    this.data.ad_groups.forEach((adGroup) => {
      const pinned = adGroup.headlines_pinned.map((text) => ({ group: adGroup.name, kind: "headline", pinned: true, text }));
      const benefit = adGroup.headlines_benefit.map((text) => ({ group: adGroup.name, kind: "headline", pinned: false, text }));
      const descriptions = adGroup.descriptions.map((text) => ({ group: adGroup.name, kind: "description", pinned: false, text }));
      const paths = adGroup.paths.map((text) => ({ group: adGroup.name, kind: "path", pinned: false, text }));
      const allInGroup = [...pinned, ...benefit, ...descriptions, ...paths];

      let keptInGroup = 0;
      for (const item of allInGroup) {
        totalAll++;
        if (!this.excluded.has(adCopyItemId(item.group, item.kind, item.text))) {
          keptInGroup++;
          totalKept++;
        }
      }

      const group = document.createElement("div");
      group.className = "group";

      const header = document.createElement("div");
      header.className = "group-header";
      header.innerHTML = `
        <span class="dot" style="background:#3ddc84"></span>
        <h2>${adGroup.name}</h2>
        <span class="group-count">${keptInGroup} / ${allInGroup.length} kept</span>
        <span class="chevron">▾</span>
      `;
      header.addEventListener("click", () => group.classList.toggle("collapsed"));
      group.appendChild(header);

      const body = document.createElement("div");
      body.className = "ac-body";

      if (adGroup.final_url) {
        const urlRow = document.createElement("div");
        urlRow.className = "ac-final-url";
        urlRow.innerHTML = `<span class="ac-final-url-label">Final URL</span><span class="ac-final-url-text">${adGroup.final_url}</span>`;
        body.appendChild(urlRow);
      }

      body.appendChild(this.renderSection(`Headlines — pinned to position 1 (${pinned.length})`, pinned));
      body.appendChild(this.renderSection(`Headlines — benefit (${benefit.length})`, benefit));
      body.appendChild(this.renderSection(`Descriptions (${descriptions.length})`, descriptions));
      body.appendChild(this.renderSection(`Display URL paths (${paths.length})`, paths));
      group.appendChild(body);

      this.mountEl.appendChild(group);
    });

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

  keptItems() {
    return this.allItems().filter((item) => !this.excluded.has(adCopyItemId(item.group, item.kind, item.text)));
  }

  exportCSV() {
    const kept = this.keptItems();
    const header = ["ad_group", "field_type", "pinned", "text", "char_count"];
    const lines = [header.join(",")];
    for (const item of kept) {
      const vals = [item.group, item.kind, item.pinned ? "yes" : "no", item.text, String(item.text.length)].map((v) => {
        const s = String(v).replace(/"/g, '""');
        return /[",\n]/.test(s) ? `"${s}"` : s;
      });
      lines.push(vals.join(","));
    }
    for (const adGroup of this.data.ad_groups) {
      if (!adGroup.final_url) continue;
      const vals = [adGroup.name, "final_url", "no", adGroup.final_url, String(adGroup.final_url.length)].map((v) => {
        const s = String(v).replace(/"/g, '""');
        return /[",\n]/.test(s) ? `"${s}"` : s;
      });
      lines.push(vals.join(","));
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
    const kept = this.keptItems();
    const all = this.allItems();
    const payload = {
      project_id: this.data.project_id,
      step: this.data.step,
      dataset_label: this.data.label,
      submitted_at: new Date().toISOString(),
      total_kept: kept.length,
      total_excluded: all.length - kept.length,
      kept_items: kept,
      final_urls: Object.fromEntries(this.data.ad_groups.filter((g) => g.final_url).map((g) => [g.name, g.final_url])),
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
      this.showStatus(`Submitted ${kept.length} lines${nextLabel ? ` — ${nextLabel}` : ""}.`, true);
      btn.textContent = "Submitted ✓";
      if (this.onApproved) this.onApproved();
    } catch (e) {
      this.showStatus("Submission failed — check your connection and try again, or use Export CSV instead.", false);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}
