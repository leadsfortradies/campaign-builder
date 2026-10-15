// Generic grouped-keyword review table, reused across steps (Step 1 groups by
// "category", Step 3 groups by "ad_group" - the data shape is the same:
// {project_id, step, label, group_label, rows: [{group, keyword, ...}]}).

const PALETTE = ["#3ddc84", "#ffb84f", "#ff6b6b", "#4f8cff", "#c97dff", "#5fd3c4", "#ff9f6b", "#8f9bff"];
const FIXED_GROUP_ORDER = ["BOF - Priority 1", "BOF - Priority 2", "Price Discovery", "Manual Review"];
const FIXED_GROUP_COLOR = {
  "BOF - Priority 1": "#3ddc84",
  "BOF - Priority 2": "#2f9e63",
  "Price Discovery": "#ffb84f",
  "Manual Review": "#ff6b6b",
};

function storageKey(projectId, step) {
  return `lft-excluded::${projectId}::${step}`;
}

function promotedStorageKey(projectId, step) {
  return `lft-promoted::${projectId}::${step}`;
}

function regroupKey(projectId, step) {
  return `lft-regroup::${projectId}::${step}`;
}

function deletedKey(projectId, step) {
  return `lft-deleted-groups::${projectId}::${step}`;
}

function loadRegrouped(projectId, step) {
  try {
    return JSON.parse(localStorage.getItem(regroupKey(projectId, step)) || "{}") || {};
  } catch (e) {
    return {};
  }
}

function loadExcluded(projectId, step) {
  try {
    const raw = localStorage.getItem(storageKey(projectId, step));
    return new Set(raw ? JSON.parse(raw) : []);
  } catch (e) {
    return new Set();
  }
}

function loadPromoted(projectId, step) {
  try {
    const raw = localStorage.getItem(promotedStorageKey(projectId, step));
    return new Set(raw ? JSON.parse(raw) : []);
  } catch (e) {
    return new Set();
  }
}

// Only "BOF - Priority 2" rows get a promote button, and they only ever
// promote to "BOF - Priority 1" - keep this mapping explicit rather than
// generic in case other steps/groups reuse this component later.
const PROMOTE_FROM = "BOF - Priority 2";
const PROMOTE_TO = "BOF - Priority 1";

function fmtBid(low, high) {
  if (low === 0 && high === 0) return "—";
  return `$${low.toFixed(2)}–$${high.toFixed(2)}`;
}

class ReviewView {
  constructor({ mountEl, statusEl, countsEl, stepData, onApproved }) {
    this.mountEl = mountEl;
    this.statusEl = statusEl;
    this.countsEl = countsEl;
    this.data = stepData;
    this.onApproved = onApproved;
    this.excluded = loadExcluded(stepData.project_id, stepData.step);
    this.promoted = loadPromoted(stepData.project_id, stepData.step);
    this.regrouped = loadRegrouped(stepData.project_id, stepData.step);
    try {
      this.deletedGroups = new Set(JSON.parse(localStorage.getItem(deletedKey(stepData.project_id, stepData.step)) || "[]"));
    } catch (e) {
      this.deletedGroups = new Set();
    }
  }

  saveDeleted() {
    try {
      localStorage.setItem(deletedKey(this.data.project_id, this.data.step), JSON.stringify([...this.deletedGroups]));
    } catch (e) { /* ignore */ }
  }

  // True when the kept keywords or their ad groups differ from what's saved in the data file.
  hasChanges() {
    return this.data.rows.some((r) => this.excluded.has(r.keyword) || this.effectiveGroup(r) !== r.group);
  }

  deleteGroup(groupName) {
    const inGroup = this.data.rows.filter((r) => this.effectiveGroup(r) === groupName);
    const label = groupName.split(" — ").slice(1).join(" — ") || groupName;
    if (!confirm(`Delete the ad group "${label}" and all ${inGroup.length} keywords in it?`)) return;
    inGroup.forEach((r) => this.excluded.add(r.keyword));
    this.deletedGroups.add(groupName);
    this.saveExcluded();
    this.saveDeleted();
    this.render();
  }

  // Re-approve Step 3 as edited (without regenerating anything), then update the
  // ad copy, extensions and landing page list to match.
  async updateAdCopy(btn) {
    const kept = this.keptRows();
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Updating…";
    try {
      let res = await fetch("/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: this.data.project_id, step: this.data.step, dataset_label: this.data.label,
          submitted_at: new Date().toISOString(), total_kept: kept.length,
          total_excluded: this.data.rows.length - kept.length, kept_keywords: kept, no_advance: true,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      res = await fetch("/api/ad-copy/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: this.data.project_id }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
      this.showStatus("Updating the ad copy and extensions. Deleted ad groups are removed, new ones get new copy. Check the Ad copy tab in a minute.", true);
      btn.textContent = "Updating ✓";
    } catch (e) {
      this.showStatus("Couldn't update the ad copy: " + e.message, false);
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  saveExcluded() {
    try {
      localStorage.setItem(
        storageKey(this.data.project_id, this.data.step),
        JSON.stringify([...this.excluded])
      );
    } catch (e) {
      /* ignore */
    }
  }

  savePromoted() {
    try {
      localStorage.setItem(
        promotedStorageKey(this.data.project_id, this.data.step),
        JSON.stringify([...this.promoted])
      );
    } catch (e) {
      /* ignore */
    }
  }

  effectiveGroup(row) {
    if (this.regrouped[row.keyword]) return this.regrouped[row.keyword];
    return row.group === PROMOTE_FROM && this.promoted.has(row.keyword) ? PROMOTE_TO : row.group;
  }

  groupOrder(groupNames) {
    const fixed = FIXED_GROUP_ORDER.filter((g) => groupNames.includes(g));
    const rest = groupNames.filter((g) => !FIXED_GROUP_ORDER.includes(g)).sort();
    return [...fixed, ...rest];
  }

  colorFor(groupName, index) {
    if (FIXED_GROUP_COLOR[groupName]) return FIXED_GROUP_COLOR[groupName];
    // Step 3 sections are "<Campaign> — <Ad Group>" - color by campaign so
    // the three campaigns stay visually distinct even though they share
    // ad-group themes.
    if (groupName.startsWith("BOF - Priority 1")) return FIXED_GROUP_COLOR["BOF - Priority 1"];
    if (groupName.startsWith("BOF - Priority 2")) return FIXED_GROUP_COLOR["BOF - Priority 2"];
    if (groupName.startsWith("Price Discovery")) return FIXED_GROUP_COLOR["Price Discovery"];
    return PALETTE[index % PALETTE.length];
  }

  render() {
    // Re-rendering rebuilds the page: keep the scroll position and which ad groups are minimised.
    const scrollY = window.scrollY;
    this.collapsed ||= new Set();
    this.mountEl.innerHTML = "";

    const byGroup = {};
    for (const row of this.data.rows) {
      (byGroup[this.effectiveGroup(row)] ||= []).push(row);
    }
    // Ad-group sections ("<Campaign> — <Ad Group>") stay on screen even when emptied, so they remain drop targets.
    for (const row of this.data.rows) if (this.canMove(row.group)) byGroup[row.group] ||= [];
    for (const g of this.deletedGroups) delete byGroup[g];
    const groupNames = this.groupOrder(Object.keys(byGroup));
    this.allGroups = groupNames;

    let totalKept = 0;
    let totalAll = 0;

    groupNames.forEach((groupName, idx) => {
      const rows = byGroup[groupName].slice().sort((a, b) => b.avg_monthly_searches - a.avg_monthly_searches);

      const group = document.createElement("div");
      group.className = "group";

      const header = document.createElement("div");
      header.className = "group-header";
      header.innerHTML = `
        <span class="dot" style="background:${this.colorFor(groupName, idx)}"></span>
        <h2>${groupName}</h2>
        <span class="group-count"></span>
        <span class="chevron">▾</span>
      `;
      if (this.collapsed.has(groupName)) group.classList.add("collapsed");
      header.addEventListener("click", () => {
        group.classList.toggle("collapsed");
        if (group.classList.contains("collapsed")) this.collapsed.add(groupName);
        else this.collapsed.delete(groupName);
      });
      if (this.canMove(groupName)) {
        const del = document.createElement("button");
        del.className = "secondary del-group-btn";
        del.textContent = "Delete ad group";
        del.title = "Delete this ad group and all its keywords";
        del.addEventListener("click", (ev) => {
          ev.stopPropagation();
          this.deleteGroup(groupName);
        });
        header.insertBefore(del, header.querySelector(".chevron"));
      }
      group.appendChild(header);
      if (this.canMove(groupName)) {
        group.addEventListener("dragover", (ev) => {
          if (this.dragKw && this.campaignOf(this.dragFrom) === this.campaignOf(groupName)) {
            ev.preventDefault();
            group.classList.add("drop-target");
          }
        });
        group.addEventListener("dragleave", (ev) => {
          if (!group.contains(ev.relatedTarget)) group.classList.remove("drop-target");
        });
        group.addEventListener("drop", (ev) => {
          ev.preventDefault();
          group.classList.remove("drop-target");
          if (this.dragKw && this.campaignOf(this.dragFrom) === this.campaignOf(groupName)) {
            this.moveKeyword(this.dragKw, groupName);
          }
          this.dragKw = null;
        });
      }

      const table = document.createElement("table");
      table.innerHTML = `
        <thead>
          <tr>
            <th class="col-kw">Keyword</th>
            <th class="col-num">Avg/mo</th>
            <th class="col-comp">Competition</th>
            <th class="col-bid">Bid range</th>
            <th class="col-promote"></th>
            ${this.canMove(groupName) ? '<th class="col-move">Move to</th>' : ""}
            <th class="col-x"></th>
          </tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");

      let keptInGroup = 0;

      for (const row of rows) {
        totalAll++;
        const isExcluded = this.excluded.has(row.keyword);
        if (!isExcluded) { keptInGroup++; totalKept++; }

        const tr = document.createElement("tr");
        tr.className = "kw-row" + (isExcluded ? " excluded" : "");
        if (this.canMove(groupName)) {
          tr.draggable = true;
          tr.addEventListener("dragstart", (ev) => {
            this.dragKw = row.keyword;
            this.dragFrom = groupName;
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", row.keyword);
            tr.classList.add("dragging");
          });
          tr.addEventListener("dragend", () => {
            tr.classList.remove("dragging");
            this.dragKw = null;
          });
        }

        const kwTd = document.createElement("td");
        kwTd.className = "col-kw";
        const kwSpan = document.createElement("span");
        kwSpan.className = "kw-text";
        kwSpan.textContent = row.keyword;
        kwTd.appendChild(kwSpan);
        if (row.note) {
          const noteDiv = document.createElement("div");
          noteDiv.className = "note";
          noteDiv.textContent = row.note;
          kwTd.appendChild(noteDiv);
        }

        const volTd = document.createElement("td");
        volTd.className = "col-num";
        volTd.textContent = row.avg_monthly_searches;

        const compTd = document.createElement("td");
        compTd.className = "col-comp";
        compTd.textContent = row.competition;

        const bidTd = document.createElement("td");
        bidTd.className = "col-bid";
        bidTd.textContent = fmtBid(row.low_bid, row.high_bid);

        const promoteTd = document.createElement("td");
        promoteTd.className = "col-promote";
        if (row.group === PROMOTE_FROM) {
          const isPromoted = this.promoted.has(row.keyword);
          const promoteBtn = document.createElement("button");
          promoteBtn.className = "promote-btn" + (isPromoted ? " active" : "");
          promoteBtn.textContent = isPromoted ? "↓ P2" : "↑ P1";
          promoteBtn.title = isPromoted
            ? "Move back to Priority 2"
            : "Move up to Priority 1";
          promoteBtn.addEventListener("click", () => this.togglePromote(row.keyword));
          promoteTd.appendChild(promoteBtn);
        }

        const xTd = document.createElement("td");
        xTd.className = "col-x";
        const xBtn = document.createElement("button");
        xBtn.className = "x-btn";
        xBtn.textContent = isExcluded ? "↺" : "✕";
        xBtn.title = isExcluded ? "Restore this keyword" : "Exclude this keyword";
        xBtn.addEventListener("click", () => this.toggleKeyword(row.keyword));
        xTd.appendChild(xBtn);

        const cells = [kwTd, volTd, compTd, bidTd, promoteTd];
        if (this.canMove(groupName)) {
          const moveTd = document.createElement("td");
          moveTd.className = "col-move";
          const sel = document.createElement("select");
          sel.className = "move-select";
          sel.title = "Move this keyword to another ad group in the same campaign";
          sel.add(new Option("Move…", ""));
          for (const g of this.allGroups) {
            if (g !== groupName && this.canMove(g) && this.campaignOf(g) === this.campaignOf(groupName)) {
              sel.add(new Option(g.split(" — ").slice(1).join(" — "), g));
            }
          }
          sel.add(new Option("+ New ad group…", "__new__"));
          sel.addEventListener("change", () => {
            if (sel.value === "__new__") {
              const name = (prompt("Name for the new ad group (e.g. Pool Fence Installation):") || "").trim();
              if (name) this.moveKeyword(row.keyword, `${this.campaignOf(groupName)} — ${name}`);
              else sel.value = "";
            } else if (sel.value) {
              this.moveKeyword(row.keyword, sel.value);
            }
          });
          moveTd.appendChild(sel);
          cells.push(moveTd);
        }
        tr.append(...cells, xTd);
        tbody.appendChild(tr);
      }

      header.querySelector(".group-count").textContent = `${keptInGroup} / ${rows.length} kept`;
      group.appendChild(table);
      this.mountEl.appendChild(group);
    });

    if (this.countsEl) {
      this.countsEl.innerHTML =
        `<span><strong>${totalKept}</strong> kept</span><span><strong>${totalAll - totalKept}</strong> excluded</span><span><strong>${totalAll}</strong> total</span>`;
    }
    window.scrollTo(0, scrollY);
    if (this.onChange) this.onChange();
  }

  // Only "<Campaign> — <Ad Group>" sections can be regrouped, and only within their own campaign.
  canMove(groupName) {
    return typeof groupName === "string" && groupName.includes(" — ");
  }

  campaignOf(groupName) {
    return (groupName || "").split(" — ")[0];
  }

  moveKeyword(keyword, targetGroup) {
    const row = this.data.rows.find((r) => r.keyword === keyword);
    if (!row || this.campaignOf(row.group) !== this.campaignOf(targetGroup)) return;
    if (targetGroup === row.group) delete this.regrouped[keyword];
    else this.regrouped[keyword] = targetGroup;
    try {
      localStorage.setItem(regroupKey(this.data.project_id, this.data.step), JSON.stringify(this.regrouped));
    } catch (e) { /* ignore */ }
    this.render();
  }

  toggleKeyword(keyword) {
    if (this.excluded.has(keyword)) {
      this.excluded.delete(keyword);
    } else {
      this.excluded.add(keyword);
    }
    this.saveExcluded();
    this.render();
  }

  // Applied from the chat box: exclude / restore a list of keywords at once.
  applyChat(exclude, restore, move) {
    exclude.forEach((k) => this.excluded.add(k));
    restore.forEach((k) => this.excluded.delete(k));
    (move || []).forEach((m) => { this.regrouped[m.keyword] = m.group; });
    try {
      localStorage.setItem(regroupKey(this.data.project_id, this.data.step), JSON.stringify(this.regrouped));
    } catch (e) { /* ignore */ }
    this.saveExcluded();
    this.render();
  }

  resetExclusions() {
    this.regrouped = {};
    try { localStorage.removeItem(regroupKey(this.data.project_id, this.data.step)); } catch (e) { /* ignore */ }
    this.excluded = new Set();
    this.deletedGroups = new Set();
    this.saveDeleted();
    this.saveExcluded();
    this.render();
  }

  togglePromote(keyword) {
    if (this.promoted.has(keyword)) {
      this.promoted.delete(keyword);
    } else {
      this.promoted.add(keyword);
    }
    this.savePromoted();
    this.render();
  }

  keptRows() {
    return this.data.rows
      .filter((r) => !this.excluded.has(r.keyword))
      .map((r) => {
        const group = this.effectiveGroup(r);
        return group === r.group ? r : { ...r, group };
      });
  }

  exportCSV() {
    const keptRows = this.keptRows();
    const header = ["group", "keyword", "avg_monthly_searches", "competition", "low_bid", "high_bid", "note"];
    const lines = [header.join(",")];
    for (const row of keptRows) {
      const vals = header.map((k) => {
        const v = row[k] ?? "";
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

  // One keyword per line (kept rows only, de-duplicated), ready to paste
  // into Google Keyword Planner.
  async copyKeywords(btn) {
    const kws = [...new Set(this.keptRows().map((r) => r.keyword))];
    const text = kws.join("\n");
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { ok = document.execCommand("copy"); } catch (e2) {}
      ta.remove();
    }
    const original = btn.textContent;
    btn.textContent = ok ? `Copied ${kws.length}` : "Copy failed";
    setTimeout(() => { btn.textContent = original; }, 1500);
  }

  showStatus(msg, ok) {
    if (!this.statusEl) return;
    this.statusEl.textContent = msg;
    this.statusEl.hidden = false;
    this.statusEl.className = `status-msg ${ok ? "ok" : "err"}`;
  }

  async submitApproval(btn, nextLabel) {
    const keptRows = this.keptRows();
    const payload = {
      project_id: this.data.project_id,
      step: this.data.step,
      dataset_label: this.data.label,
      submitted_at: new Date().toISOString(),
      total_kept: keptRows.length,
      total_excluded: this.data.rows.length - keptRows.length,
      kept_keywords: keptRows,
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
      this.showStatus(`Submitted ${keptRows.length} keywords${nextLabel ? ` — ${nextLabel}` : ""}.`, true);
      btn.textContent = "Submitted ✓";
      if (this.onApproved) this.onApproved();
    } catch (e) {
      this.showStatus("Submission failed — check your connection and try again, or use Export CSV instead.", false);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}
