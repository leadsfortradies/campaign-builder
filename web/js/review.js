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

function loadExcluded(projectId, step) {
  try {
    const raw = localStorage.getItem(storageKey(projectId, step));
    return new Set(raw ? JSON.parse(raw) : []);
  } catch (e) {
    return new Set();
  }
}

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
    this.mountEl.innerHTML = "";

    const byGroup = {};
    for (const row of this.data.rows) {
      (byGroup[row.group] ||= []).push(row);
    }
    const groupNames = this.groupOrder(Object.keys(byGroup));

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
      header.addEventListener("click", () => group.classList.toggle("collapsed"));
      group.appendChild(header);

      const table = document.createElement("table");
      table.innerHTML = `
        <thead>
          <tr>
            <th class="col-kw">Keyword</th>
            <th class="col-num">Avg/mo</th>
            <th class="col-comp">Competition</th>
            <th class="col-bid">Bid range</th>
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

        const xTd = document.createElement("td");
        xTd.className = "col-x";
        const xBtn = document.createElement("button");
        xBtn.className = "x-btn";
        xBtn.textContent = isExcluded ? "↺" : "✕";
        xBtn.title = isExcluded ? "Restore this keyword" : "Exclude this keyword";
        xBtn.addEventListener("click", () => this.toggleKeyword(row.keyword));
        xTd.appendChild(xBtn);

        tr.append(kwTd, volTd, compTd, bidTd, xTd);
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

  resetExclusions() {
    this.excluded = new Set();
    this.saveExcluded();
    this.render();
  }

  keptRows() {
    return this.data.rows.filter((r) => !this.excluded.has(r.keyword));
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
