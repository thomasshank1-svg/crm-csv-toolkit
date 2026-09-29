let state = { stages: [], leads: [], totals: {} };

function renderStats() {
  $("#stats").innerHTML = state.stages.map((stage) => `
    <div class="stat">
      <strong>${money(state.totals[stage] || 0)}</strong>
      <span>${esc(stage)}</span>
    </div>
  `).join("");
}

function renderStageOptions() {
  $("#stageSelect").innerHTML = state.stages.map((stage) => `<option>${esc(stage)}</option>`).join("");
}

function renderLeads() {
  $("#leads").innerHTML = state.leads.map((lead) => `
    <article class="item lead">
      <div>
        <h3>${esc(lead.name)}</h3>
        <p>${esc(lead.company)}<br><span class="muted">${esc(lead.email)}</span></p>
        <span class="pill">${money(lead.value_cents)}</span>
      </div>
      <div>
        <select data-stage="${lead.id}">
          ${state.stages.map((stage) => `<option ${stage === lead.stage ? "selected" : ""}>${esc(stage)}</option>`).join("")}
        </select>
        <p class="small muted">${esc(lead.notes || "No notes")}</p>
      </div>
    </article>
  `).join("");
  document.querySelectorAll("[data-stage]").forEach((select) => {
    select.addEventListener("change", () => action(select, async () => {
      await api("/api/stage", { id: Number(select.dataset.stage), stage: select.value });
      await refresh();
    }));
  });
}

async function refresh() {
  state = await api("/api/state");
  renderStageOptions();
  renderStats();
  renderLeads();
}

$("#leadForm").addEventListener("submit", (event) => {
  event.preventDefault();
  action(event.submitter, async () => {
    await api("/api/leads", Object.fromEntries(new FormData(event.currentTarget)));
    event.currentTarget.reset();
    await refresh();
    toast("Lead added.");
  });
});

$("#importForm").addEventListener("submit", (event) => {
  event.preventDefault();
  action(event.submitter, async () => {
    const result = await api("/api/import", Object.fromEntries(new FormData(event.currentTarget)));
    await refresh();
    toast(`${result.imported} imported, ${result.skipped} skipped.`);
  });
});

$("#download").addEventListener("click", () => action($("#download"), async () => {
  const result = await api("/api/export");
  const blob = new Blob([result.csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "pipeline-leads.csv";
  link.click();
  URL.revokeObjectURL(url);
}));

refresh().catch((error) => toast(error.message));
