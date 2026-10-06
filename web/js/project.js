const STEP_ORDER = ["step1", "step2", "step3", "step4", "step5", "step6"];

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

function setTab(step) {
  const url = new URL(location.href);
  url.searchParams.set("step", step);
  history.replaceState(null, "", url);
}

async function init() {
  const projectId = qs("id");
  const content = document.getElementById("content");
  const titleEl = document.getElementById("project-title");

  if (!projectId) {
    titleEl.textContent = "No project specified";
    return;
  }

  const res = await fetch("projects.json");
  const projects = await res.json();
  const project = projects.find((p) => p.id === projectId);

  if (!project) {
    titleEl.textContent = "Project not found";
    content.innerHTML = `<p class="empty-state">No project with id "${projectId}".</p>`;
    return;
  }

  titleEl.textContent = project.label;

  const availableSteps = STEP_ORDER.filter((s) => project.steps?.[s]);
  const tabsEl = document.getElementById("tabs");
  let activeStep = qs("step");
  if (!availableSteps.includes(activeStep)) activeStep = availableSteps[0];

  function renderTabs() {
    tabsEl.innerHTML = "";
    for (const step of availableSteps) {
      const info = project.steps[step];
      const btn = document.createElement("button");
      btn.className = "tab-btn" + (step === activeStep ? " active" : "");
      const dotColor = info.status === "approved" ? "#3ddc84" : info.status === "skipped" ? "#9aa1ac" : "#ffb84f";
      btn.innerHTML = `<span class="tab-dot" style="background:${dotColor}"></span>${info.step_label || step}`;
      btn.addEventListener("click", () => {
        activeStep = step;
        setTab(step);
        renderTabs();
        renderContent();
      });
      tabsEl.appendChild(btn);
    }
  }

  async function renderContent() {
    const toolbar = document.getElementById("toolbar");
    const statusMsg = document.getElementById("status-msg");
    statusMsg.hidden = true;
    content.innerHTML = "";

    const info = project.steps[activeStep];

    if (info.status === "skipped") {
      toolbar.hidden = true;
      content.innerHTML = `<div class="skip-note"><strong>Skipped.</strong> ${info.note || "No reason given."}</div>`;
      return;
    }

    toolbar.hidden = false;
    const dataRes = await fetch(info.file);
    const stepData = await dataRes.json();

    const ViewClass =
      activeStep === "step5" ? LandingPagesView :
      activeStep === "step6" ? SitelinksView :
      stepData.ad_groups ? AdCopyView : ReviewView;
    const view = new ViewClass({
      mountEl: content,
      statusEl: statusMsg,
      countsEl: document.getElementById("counts"),
      stepData,
      onApproved: () => {
        info.status = "approved";
        renderTabs();
      },
    });
    view.render();

    document.getElementById("reset-btn").onclick = () => view.resetExclusions();
    document.getElementById("export-btn").onclick = () => view.exportCSV();
    document.getElementById("approve-btn").onclick = (e) => view.submitApproval(e.target, "tell Claude you're ready and it'll pick this up");
  }

  renderTabs();
  renderContent();
}

init();
