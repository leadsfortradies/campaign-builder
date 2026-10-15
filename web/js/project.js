const STEP_ORDER = ["step1", "step2", "campaigns", "step3", "step4", "step6", "step5"];
// Sitelinks (step6 key) now runs before Landing Pages (step5 key); data keys unchanged.
const STEP_TITLES = { step6: "Step 5: Sitelinks, Callouts & Snippets", step5: "Step 6: Landing Pages" };

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

function setTab(step) {
  const url = new URL(location.href);
  url.searchParams.set("step", step);
  history.replaceState(null, "", url);
}

async function showMissingInfo(projectId) {
  const el = document.getElementById("info-line");
  let d = {};
  try {
    const r = await fetch(`data/${encodeURIComponent(projectId)}/step0.json`);
    if (r.ok) d = await r.json();
  } catch (e) { /* none yet */ }
  const missing = [];
  if (!(d.services || []).length || !(d.service_areas || []).length) {
    missing.push("services / service area (needed for keyword research)");
  }
  if (!d.business_name || !["years_experience", "completed_projects", "certifications", "other_info"].some((f) => d[f] && d[f].length)) {
    missing.push("business details (needed for ad copy)");
  }
  if (!d.business_logo_path) missing.push("logo (needed to finish landing pages)");
  if (!(d.work_photo_paths || []).length) missing.push("work photos (needed to finish landing pages)");
  const link = `<a href="new.html?id=${encodeURIComponent(projectId)}">${missing.length ? "Add business info" : "Edit business info"}</a>`;
  el.innerHTML = missing.length
    ? `Still missing: ${missing.join("; ")}. ${link}`
    : link;
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
  showMissingInfo(project.id);

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
      btn.innerHTML = `<span class="tab-dot" style="background:${dotColor}"></span>${STEP_TITLES[step] || info.step_label || step}`;
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
      activeStep === "campaigns" ? CampaignsView :
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
    if (activeStep === "step6" && project.steps.step4?.file) {
      try {
        view.adCopyData = await (await fetch(project.steps.step4.file)).json();
      } catch (e) {
        /* PDF just won't include ad copy */
      }
    }
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

    const chatForm = document.getElementById("chat-form");
    const chatReply = document.getElementById("chat-reply");
    chatReply.hidden = true;
    chatForm.hidden = typeof view.applyChat !== "function";
    chatForm.onsubmit = async (ev) => {
      ev.preventDefault();
      const input = document.getElementById("chat-input");
      const send = document.getElementById("chat-send");
      const message = input.value.trim();
      if (!message) return;
      send.disabled = true;
      send.textContent = "Thinking…";
      try {
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: project.id, step: activeStep, message,
            excluded: [...view.excluded], regrouped: view.regrouped || {},
          }),
        });
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
        const out = await r.json();
        view.applyChat(out.exclude, out.restore, out.move);
        const bits = [];
        if (out.exclude.length) bits.push(`excluded ${out.exclude.length}`);
        if (out.restore.length) bits.push(`restored ${out.restore.length}`);
        if ((out.move || []).length) bits.push(`moved ${out.move.length}`);
        chatReply.textContent = [out.reply, bits.length ? `(${bits.join(", ")})` : ""].filter(Boolean).join(" ");
        chatReply.className = "status-msg ok";
        input.value = "";
      } catch (err) {
        chatReply.textContent = "Couldn't do that: " + err.message;
        chatReply.className = "status-msg err";
      }
      chatReply.hidden = false;
      send.disabled = false;
      send.textContent = "Send";
    };

    for (const id of ["reset-btn", "export-btn", "copy-btn", "changes-btn"]) {
      if (activeStep === "campaigns") document.getElementById(id).hidden = true;
      else if (id !== "copy-btn") document.getElementById(id).hidden = false;
    }
    document.getElementById("changes-panel").hidden = true;
    document.getElementById("reset-btn").onclick = () => view.resetExclusions && view.resetExclusions();
    document.getElementById("export-btn").onclick = () => view.exportCSV && view.exportCSV();
    const pdfBtn = document.getElementById("pdf-btn");
    pdfBtn.hidden = typeof view.exportPDF !== "function";
    pdfBtn.onclick = () => view.exportPDF();
    const copyBtn = document.getElementById("copy-btn");
    copyBtn.hidden = typeof view.copyKeywords !== "function" || activeStep === "campaigns";
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
    if (status === "blocked") {
      const a = document.createElement("a");
      a.href = `new.html?id=${encodeURIComponent(project.id)}`;
      a.textContent = "Add business info";
      a.className = "new-btn";
      div.appendChild(a);
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

  async function showCost() {
    const el = document.getElementById("cost-line");
    try {
      const r = await fetch(`/api/projects/${encodeURIComponent(project.id)}/cost`);
      if (!r.ok) return;
      const c = await r.json();
      const names = { step1: "Keywords", step2: "Location keywords", campaigns: "Campaigns", step3: "Ad groups",
        step4: "Ad copy", step6: "Sitelinks", step5: "Landing pages", chat: "Chat edits" };
      const lines = Object.entries(c.by_step)
        .sort((a, b) => b[1].usd - a[1].usd)
        .map(([s, v]) => `${names[s] || s}: US$${v.usd.toFixed(2)}`);
      el.textContent = `Claude API cost so far: US$${c.total_usd.toFixed(2)} (${(c.tokens_used / 1000).toFixed(0)}k tokens)`;
      el.title = (lines.join("\n") || "No Claude usage yet") +
        "\n\nEstimate from list prices; your Anthropic invoice is the source of truth." +
        (c.unpriced_models.length ? `\nNo price set for: ${c.unpriced_models.join(", ")}` : "");
      el.hidden = false;
    } catch (e) { /* older server without the cost API */ }
  }

  renderTabs();
  renderContent();
  showJobs();
  showCost();
  setInterval(showCost, 30000);
  setInterval(showJobs, 5000);
}

init();
