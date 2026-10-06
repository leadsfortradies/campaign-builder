const STEP_ORDER = ["step1", "step2", "step3", "step4"];

function badgeLabel(stepKey, stepInfo) {
  if (!stepInfo) return `${stepKey}: not started`;
  if (stepInfo.status === "skipped") return `${stepInfo.step_label || stepKey}: skipped`;
  if (stepInfo.status === "approved") {
    const count = stepInfo.approved_count ?? stepInfo.row_count;
    return `${stepInfo.step_label || stepKey}: approved (${count})`;
  }
  return `${stepInfo.step_label || stepKey}: ${stepInfo.row_count ?? "?"} to review`;
}

async function init() {
  const res = await fetch("projects.json");
  const projects = await res.json();

  const listEl = document.getElementById("project-list");

  if (projects.length === 0) {
    listEl.outerHTML = '<p class="empty-state">No projects yet.</p>';
    return;
  }

  for (const project of projects) {
    const card = document.createElement("a");
    card.className = "project-card";
    card.href = `project.html?id=${encodeURIComponent(project.id)}`;

    const badges = STEP_ORDER.map((stepKey) => {
      const info = project.steps?.[stepKey];
      const status = info ? info.status : "not_started";
      return `<span class="badge ${status}">${badgeLabel(stepKey, info)}</span>`;
    }).join("");

    card.innerHTML = `
      <h2>${project.label}</h2>
      <div class="badge-row">${badges}</div>
    `;
    listEl.appendChild(card);
  }
}

init();
