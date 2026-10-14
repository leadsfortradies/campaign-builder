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

    // Step is being worked on (or stuck) and has no reviewable data yet.
    if (!info.file || ["queued", "running", "blocked", "failed"].includes(info.status)) {
      toolbar.hidden = true;
      await renderJobStatus(activeStep);
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

    const warned = (stepData.ad_groups || []).filter((g) => g.warnings && g.warnings.length);
    if (warned.length) {
      const w = document.createElement("div");
      w.className = "warn-list";
      w.innerHTML = "<strong>Check these before approving:</strong>";
      const ul = document.createElement("ul");
      for (const g of warned) for (const msg of g.warnings) {
        const li = document.createElement("li");
        li.textContent = `${g.name}: ${msg}`;
        ul.appendChild(li);
      }
      w.appendChild(ul);
      content.prepend(w);
    }

    document.getElementById("reset-btn").onclick = () => view.resetExclusions();
    document.getElementById("export-btn").onclick = () => view.exportCSV();
    const copyBtn = document.getElementById("copy-btn");
    copyBtn.hidden = typeof view.copyKeywords !== "function";
    copyBtn.onclick = () => view.copyKeywords(copyBtn);
    document.getElementById("approve-btn").onclick = (e) => view.submitApproval(e.target, "the next step is queued");
  }

  document.getElementById("changes-btn").onclick = () => {
    const panel = document.getElementById("changes-panel");
    panel.hidden = !panel.hidden;
  };
  document.getElementById("changes-send").onclick = async (e) => {
    const note = document.getElementById("changes-note").value.trim();
    const statusMsg = document.getElementById("status-msg");
    if (!note) return;
    e.target.disabled = true;
    try {
      const r = await fetch("/api/request-changes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: project.id, step: activeStep, note }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      statusMsg.textContent = "Change request sent.";
      statusMsg.className = "status-msg ok";
      document.getElementById("changes-note").value = "";
      document.getElementById("changes-panel").hidden = true;
    } catch (err) {
      statusMsg.textContent = "Couldn't send changes: " + err.message;
      statusMsg.className = "status-msg err";
    }
    statusMsg.hidden = false;
    e.target.disabled = false;
    showJobs();
  };

  async function renderJobStatus(step) {
    let job = null;
    try {
      const r = await fetch(`/api/jobs?project_id=${encodeURIComponent(project.id)}&limit=20`);
      if (r.ok) job = (await r.json()).find((j) => j.step === step);
      if (job) job = await (await fetch(`/api/jobs/${job.id}`)).json();
    } catch (e) { /* ignore */ }
    const status = job ? job.status : info_status(step);
    const heading = {
      queued: "Queued, starting shortly…", running: "Working on it…",
      blocked: "Needs you", failed: "Something went wrong", done: "Finished",
    }[status] || status;
    const div = document.createElement("div");
    div.className = "step-status";
    div.innerHTML = `<strong>${heading}</strong>`;
    if (job && job.error) {
      const p = document.createElement("p");
      p.textContent = job.error.split("\n")[0];
      div.appendChild(p);
    }
    if (job && job.log) {
      const pre = document.createElement("pre");
      pre.textContent = job.log;
      div.appendChild(pre);
    }
    if (["blocked", "failed"].includes(status)) {
      const btn = document.createElement("button");
      btn.className = "primary";
      btn.textContent = "Retry this step";
      btn.onclick = async () => {
        btn.disabled = true;
        await fetch("/api/retry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: project.id, step }),
        });
        location.reload();
      };
      div.appendChild(btn);
    }
    content.innerHTML = "";
    content.appendChild(div);
    if (["queued", "running"].includes(status)) {
      setTimeout(() => location.reload(), 8000);
    }
  }

  function info_status(step) {
    return (project.steps[step] || {}).status;
  }

  async function showJobs() {
    const el = document.getElementById("job-msg");
    try {
      const r = await fetch(`/api/jobs?project_id=${encodeURIComponent(project.id)}&limit=1`);
      if (!r.ok) return;
      const [job] = await r.json();
      if (!job || job.status === "done") { el.hidden = true; return; }
      const text = {
        queued: "Queued", running: "Running",
        blocked: job.error || "Waiting on you", failed: "Failed: " + (job.error || "").split("\n")[0],
      }[job.status] || job.status;
      el.textContent = `Latest job (${job.step}): ${text}`;
      el.className = "status-msg " + (job.status === "failed" ? "err" : "ok");
      el.hidden = false;
    } catch (e) { /* old local server has no jobs API */ }
  }

  renderTabs();
  renderContent();
  showJobs();
  setInterval(showJobs, 5000);
}

init();
