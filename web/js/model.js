// Shows which Claude model the backend is using and lets the user switch it.
// Silently does nothing on the old local server (no /api/settings there).
(async function () {
  let data;
  try {
    const r = await fetch("/api/settings");
    if (!r.ok) return;
    data = await r.json();
  } catch (e) { return; }

  const wrap = document.createElement("label");
  wrap.className = "model-picker";
  wrap.innerHTML = '<span>Model</span>';
  const sel = document.createElement("select");
  for (const m of data.models) {
    const o = document.createElement("option");
    o.value = m.id;
    o.textContent = `${m.label} — ${m.note}`;
    if (m.id === data.model) o.selected = true;
    sel.appendChild(o);
  }
  const note = document.createElement("small");
  note.textContent = "Applies from the next job";
  note.hidden = true;
  sel.addEventListener("change", async () => {
    const r = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: sel.value }),
    });
    note.textContent = r.ok ? "Saved — applies from the next job" : "Couldn't save";
    note.hidden = false;
  });
  wrap.appendChild(sel);
  wrap.appendChild(note);
  document.querySelector("header").prepend(wrap);
})();
