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
        <h2>${adGroup.theme || adGroup.name}</h2>
        ${adGroup.campaign ? `<span class="ac-campaign">${adGroup.campaign}</span>` : ""}
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

// Client-facing approval PDF: ad copy (kept lines only) followed by the
// extensions (sitelinks, callouts, snippets). Opens the browser print dialog
// via a hidden iframe - choose "Save as PDF". Called from the extensions view.
function exportApprovalPDF({ label, adCopy, adCopyExcluded, extensions, extensionsExcluded }) {
  const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const logo = new URL("images/lft-logo.png", location.href).href;
  const date = new Date().toLocaleDateString("en-NZ", { day: "numeric", month: "long", year: "numeric" });
  const list = (title, arr, tag) =>
    arr.length
      ? `<h3>${title}</h3><ul>${arr.map((t) => `<li>${esc(t)}${tag ? `<span class="tag">${tag}</span>` : ""}</li>`).join("")}</ul>`
      : "";

  let body = "";
  if (adCopy) {
    body += adCopy.ad_groups.map((g) => {
      const keep = (kind, t) => !adCopyExcluded.has(adCopyItemId(g.name, kind, t));
      const pinned = g.headlines_pinned.filter((t) => keep("headline", t));
      const benefit = g.headlines_benefit.filter((t) => keep("headline", t));
      const descs = g.descriptions.filter((t) => keep("description", t));
      const paths = g.paths.filter((t) => keep("path", t));
      return `<section class="group">
        <h2>${esc(g.name)}</h2>
        ${g.final_url ? `<p class="url">${esc(g.final_url)}</p>` : ""}
        ${list("Headlines", pinned, "Shown first")}
        ${list("Additional headlines", benefit)}
        ${list("Descriptions", descs)}
        ${paths.length ? `<h3>Display URL paths</h3><p class="paths">${paths.map((t) => `/${esc(t)}`).join("&nbsp;&nbsp;·&nbsp;&nbsp;")}</p>` : ""}
      </section>`;
    }).join("");
  }

  if (extensions) {
    const out = extensionsExcluded;
    const sitelinkGroups = extensions.ad_groups.map((g) => {
      const items = g.sitelinks.filter((_, i) => !out.has(sitelinkId(g.name, i)));
      if (!items.length) return "";
      return `<h3>${esc(g.name)}</h3><ul>${items.map((sl) => `<li><strong>${esc(sl.text)}</strong><br>
        <span class="sub">${esc(sl.description_1)} · ${esc(sl.description_2)}</span><br>
        <span class="url">${esc(sl.url)}</span></li>`).join("")}</ul>`;
    }).join("");
    if (sitelinkGroups) body += `<section class="group"><h2>Sitelinks</h2>${sitelinkGroups}</section>`;

    const callouts = (extensions.callouts || []).filter((_, i) => !out.has(calloutId(i)));
    if (callouts.length) body += `<section class="group"><h2>Callouts</h2>${list("Shown across all ad groups", callouts)}</section>`;

    const snip = extensions.structured_snippets;
    const values = ((snip && snip.values) || []).filter((_, i) => !out.has(snippetId(i)));
    if (values.length) body += `<section class="group"><h2>Structured snippets</h2>${list(esc(snip.header || "Snippet"), values)}</section>`;
  }

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(label)} - Ad Copy</title>
<link href="https://fonts.googleapis.com/css2?family=Karla:wght@400;700&family=Oswald:wght@500;600&display=swap" rel="stylesheet">
<style>
  @page { size: A4; margin: 14mm 14mm 16mm; }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font-family: Karla, Arial, sans-serif; color: #1c231f; margin: 0; font-size: 11pt; line-height: 1.4; }
  .banner { background: #141c19; color: #f2ecdd; padding: 18px 22px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; }
  .banner img { height: 40px; }
  .banner .meta { text-align: right; font-size: 9.5pt; color: #c9c5b4; }
  .banner .meta strong { color: #e8b463; font-family: Oswald, sans-serif; font-weight: 500; letter-spacing: .04em; text-transform: uppercase; display: block; font-size: 11pt; }
  h1 { font-family: Oswald, sans-serif; font-weight: 600; font-size: 24pt; margin: 22px 0 4px; text-transform: uppercase; letter-spacing: .02em; }
  .intro { color: #5a6359; margin: 0 0 8px; }
  .group { border: 1px solid #d9d4c2; border-left: 5px solid #e8b463; border-radius: 6px; padding: 14px 18px; margin: 16px 0; break-inside: avoid-page; }
  h2 { font-family: Oswald, sans-serif; font-weight: 500; font-size: 15pt; margin: 0 0 2px; }
  h3 { font-size: 9pt; text-transform: uppercase; letter-spacing: .08em; color: #8a6a2a; margin: 12px 0 4px; }
  .url { margin: 0; font-size: 9pt; color: #8f9787; word-break: break-all; }
  .sub { color: #5a6359; font-size: 10pt; }
  ul { margin: 0; padding: 0; list-style: none; }
  li { padding: 4px 0; border-bottom: 1px solid #efebdc; }
  li:last-child { border-bottom: 0; }
  .tag { float: right; font-size: 8pt; background: #fbf1da; color: #8a6a2a; border-radius: 10px; padding: 1px 8px; }
  .paths { margin: 0; }
  .foot { margin-top: 22px; padding-top: 10px; border-top: 2px solid #e8b463; font-size: 9pt; color: #5a6359; }
</style></head><body>
  <div class="banner"><img src="${logo}" alt="Leads For Tradies">
    <div class="meta"><strong>Google Ads copy for approval</strong>${esc(date)}</div></div>
  <h1>${esc(label)}</h1>
  <p class="intro">Please review the ad copy and extensions below and let us know if you'd like anything changed.</p>
  ${body}
  <div class="foot">Leads For Tradies · 027 824 6725 · liam@leadsfortradies.co.nz · leadsfortradies.co.nz</div>
</body></html>`;

  const frame = document.createElement("iframe");
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  document.body.appendChild(frame);
  const doc = frame.contentWindow.document;
  doc.open();
  doc.write(html);
  doc.close();
  const finish = () => {
    frame.contentWindow.focus();
    frame.contentWindow.print();
    setTimeout(() => frame.remove(), 60000);
  };
  // wait for logo + web fonts so the PDF isn't missing them
  const ready = Promise.all([
    new Promise((r) => { const img = doc.images[0]; if (!img || img.complete) r(); else { img.onload = r; img.onerror = r; } }),
    doc.fonts ? doc.fonts.ready.catch(() => {}) : Promise.resolve(),
  ]);
  Promise.race([ready, new Promise((r) => setTimeout(r, 4000))]).then(finish);
}
