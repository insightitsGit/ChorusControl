let token = localStorage.getItem("cc_token") || "";
let headers = {
  Authorization: "Bearer " + (token || "pending"),
  "Content-Type": "application/json",
};

function setToken(next) {
  token = (next || "").trim();
  if (token) localStorage.setItem("cc_token", token);
  headers = {
    Authorization: "Bearer " + token,
    "Content-Type": "application/json",
  };
  const input = document.getElementById("apiToken");
  if (input && input.value !== token) input.value = token;
}

async function resolveToken() {
  const input = document.getElementById("apiToken");
  const demoFromPage = (input?.dataset.demoToken || "").trim();
  const stored = (localStorage.getItem("cc_token") || "").trim();
  const candidates = [];
  const push = (t) => {
    if (t && !candidates.includes(t)) candidates.push(t);
  };
  push(stored);
  push(demoFromPage);
  push("healthcare-demo-token");
  push("dev-admin-token");

  try {
    const auth = await fetch("/api/v1/admin/auth").then((r) => r.json());
    if (auth.demo_token) push(auth.demo_token);
    for (const c of auth.demo_token_candidates || []) push(c);
    if (auth.demo_mode) {
      const banner = document.getElementById("demoBanner");
      if (banner) banner.hidden = false;
    }
  } catch (_) {
    /* open auth endpoint should always work */
  }

  for (const cand of candidates) {
    try {
      const r = await fetch("/api/v1/admin/license", {
        headers: { Authorization: "Bearer " + cand },
      });
      if (r.ok) {
        setToken(cand);
        document.getElementById("authBanner").hidden = true;
        return true;
      }
    } catch (_) {}
  }
  if (demoFromPage) setToken(demoFromPage);
  else if (stored) setToken(stored);
  document.getElementById("authBanner").hidden = false;
  return false;
}

const tab = document.getElementById("main").dataset.tab;
const view = document.getElementById("view");
const actions = document.getElementById("actions");
const out = document.getElementById("out");

// Prefill token box immediately for UX
(() => {
  const input = document.getElementById("apiToken");
  if (!input) return;
  const initial = localStorage.getItem("cc_token") || input.dataset.demoToken || "";
  if (initial) input.value = initial;
  document.getElementById("applyToken")?.addEventListener("click", () => {
    setToken(input.value);
    document.getElementById("authBanner").hidden = true;
    load();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      setToken(input.value);
      document.getElementById("authBanner").hidden = true;
      load();
    }
  });
})();

const blurbs = {
  overview: "Live health of the Prism stack — caps, fleet posture, and a transparent AI Score.",
  trace: "Stitched Guard → Ledger → Shine wire. Replay is zero-token from cache.",
  taxonomy: "Knowledge partitions, chunk health, and maintenance jobs.",
  memory: "Bitemporal facts and conflict resolution with correction cascade.",
  cortex: "PrismCortex activity, memory graph chunks, digest / recall / sleep.",
  guard: "Policy Studio for ingress profiles — hub paths never force law ONNX.",
  admin: "License, doctor, fleet enrollment, Asset Graph, incidents, and compliance.",
};

let viewMode = localStorage.getItem("cc_view_mode") || "ops";
function setViewMode(mode) {
  viewMode = mode;
  localStorage.setItem("cc_view_mode", mode);
  document.body.dataset.viewMode = mode;
  if (typeof lastRender === "function") lastRender();
}

const eyebrows = {
  overview: "Command center",
  trace: "Execution truth",
  taxonomy: "Knowledge ops",
  memory: "Cortex memory",
  cortex: "PrismCortex",
  guard: "Security governance",
  admin: "Platform control",
};

document.getElementById("blurb").textContent = blurbs[tab] || "";
document.getElementById("eyebrow").textContent = eyebrows[tab] || "Operations platform";
document.getElementById("heading").textContent =
  tab === "overview" ? "Overview" : tab.charAt(0).toUpperCase() + tab.slice(1);

document.getElementById("navToggle")?.addEventListener("click", () => {
  document.body.classList.toggle("nav-open");
});

/* ————— Theme ————— */
function cssVar(name, fallback = "") {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

let lastRender = null; // re-run current tab render on theme flip (charts/viz pick up new palette)

function setTheme(next) {
  const theme = next === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("cc_theme", theme);
  document.querySelectorAll("[data-theme-set]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.getAttribute("data-theme-set") === theme);
  });
  if (lastRender) requestAnimationFrame(() => lastRender());
}

setTheme(document.documentElement.getAttribute("data-theme") || "dark");

document.querySelectorAll("[data-theme-set]").forEach((btn) => {
  btn.addEventListener("click", () => setTheme(btn.getAttribute("data-theme-set")));
});

document.getElementById("themeToggle")?.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  setTheme(cur === "dark" ? "light" : "dark");
});

function setChatOpen(open) {
  document.body.classList.toggle("chat-open", open);
  if (open) document.getElementById("chatInput")?.focus();
}
document.getElementById("openChat")?.addEventListener("click", () => setChatOpen(true));
document.getElementById("fabChat")?.addEventListener("click", () => setChatOpen(true));
document.getElementById("closeChat")?.addEventListener("click", () => setChatOpen(false));

let pendingExecute = null;

function appendChat(role, html) {
  const log = document.getElementById("chatLog");
  if (!log) return;
  const div = document.createElement("div");
  div.className = "bubble " + role;
  div.innerHTML = html;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function showTyping() {
  const log = document.getElementById("chatLog");
  if (!log) return () => {};
  const div = document.createElement("div");
  div.className = "bubble bot typing";
  div.innerHTML = "<i></i><i></i><i></i>";
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return () => div.remove();
}

async function askAssistant(question, { confirm = false, execute = null } = {}) {
  appendChat("user", escapeHtml(question));
  const body = { question, tenant_id: "default", confirm, execute };
  const stopTyping = showTyping();
  let r;
  try {
    r = await j("/api/v1/assistant/ask", { method: "POST", body: JSON.stringify(body) });
  } finally {
    stopTyping();
  }
  let html = formatAssistantText(r.answer || "");
  const g = r.grounding || {};
  const w = r.wire || {};
  const wireBits = [];
  if (w.guard?.decision) wireBits.push(`Guard ${String(w.guard.decision).toUpperCase()}`);
  if (w.graph?.hops?.length) wireBits.push(`Graph ${w.graph.hops.join("→")}`);
  if (w.shine?.decision) wireBits.push(`Shine ${String(w.shine.decision).toUpperCase()}`);
  if (w.mode) wireBits.push(w.mode === "live" ? "live wire" : "fallback");
  if (g.ai_score != null || wireBits.length) {
    html =
      `<div class="score-meta" style="margin-bottom:0.45rem">${
        g.ai_score != null
          ? `Live grounding · AI Score <strong>${escapeHtml(String(g.ai_score))}</strong> · agents ${escapeHtml(
              String(g.online ?? "?")
            )}/${escapeHtml(String(g.nodes ?? "?"))} · incidents ${escapeHtml(String(g.incidents ?? 0))}${
              g.demo ? " · DEMO" : ""
            }`
          : ""
      }${
        wireBits.length
          ? `${g.ai_score != null ? "<br/>" : ""}<span class="wire-chips">${wireBits
              .map((b) => `<span class="wire-chip">${escapeHtml(b)}</span>`)
              .join("")}</span>`
          : ""
      }</div>` + html;
  }
  if (r.actions?.length) {
    html += `<div style="margin-top:0.5rem">${r.actions
      .map(
        (a, i) =>
          `<button type="button" class="btn secondary" style="margin:0.2rem 0.2rem 0 0;font-size:0.72rem" data-exec='${escapeHtml(
            JSON.stringify(a)
          )}' data-qi="${i}">${escapeHtml(a.command || a.type || "action")}</button>`
      )
      .join("")}</div>`;
  }
  if (r.disclaimer) html += `<span class="disclaimer">${escapeHtml(r.disclaimer)}</span>`;
  appendChat("bot", html);
  if (r.execution) {
    appendChat("bot", `<strong>Execution:</strong> ${escapeHtml(JSON.stringify(r.execution))}`);
  }
  document.querySelectorAll("[data-exec]").forEach((btn) => {
    btn.onclick = () => {
      try {
        pendingExecute = JSON.parse(btn.getAttribute("data-exec"));
        document.getElementById("chatConfirm").hidden = false;
        document.getElementById("chatConfirmMsg").textContent =
          "Confirm gated action: " + JSON.stringify(pendingExecute);
      } catch (_) {}
    };
  });
  return r;
}

function formatAssistantText(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.getElementById("chatForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const q = (input.value || "").trim();
  if (!q) return;
  input.value = "";
  try {
    await askAssistant(q);
  } catch (err) {
    appendChat("bot", `<span class="err">${escapeHtml(String(err.message || err))}</span>`);
  }
});

document.getElementById("chatSuggest")?.addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-q]");
  if (!b) return;
  try {
    await askAssistant(b.dataset.q);
  } catch (err) {
    appendChat("bot", `<span class="err">${escapeHtml(String(err.message || err))}</span>`);
  }
});

document.getElementById("chatConfirmCancel")?.addEventListener("click", () => {
  pendingExecute = null;
  document.getElementById("chatConfirm").hidden = true;
});

document.getElementById("chatConfirmOk")?.addEventListener("click", async () => {
  if (!pendingExecute) return;
  const exec = pendingExecute;
  pendingExecute = null;
  document.getElementById("chatConfirm").hidden = true;
  try {
    await askAssistant("Execute confirmed action", { confirm: true, execute: exec });
  } catch (err) {
    appendChat("bot", `<span class="err">${escapeHtml(String(err.message || err))}</span>`);
  }
});

async function j(url, opts = {}) {
  const r = await fetch(url, { headers, ...opts });
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("application/zip")) return r;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = data.detail;
    const msg =
      (detail && (detail.message || (typeof detail === "string" ? detail : JSON.stringify(detail)))) ||
      r.statusText;
    throw Object.assign(new Error(msg), { data, status: r.status });
  }
  return data;
}

function status(ok, label) {
  return `<span class="status ${ok ? "ok" : "bad"}">${label}</span>`;
}

function section(title, body, hint = "", delay = 0) {
  return `<section class="section" style="animation-delay:${delay}ms">
    <div class="section-head"><h2>${title}</h2>${hint ? `<span class="hint">${hint}</span>` : ""}</div>
    <div class="surface">${body}</div>
  </section>`;
}

function btn(label, id, kind = "") {
  const cls = kind === "danger" ? "danger" : kind === "secondary" ? "secondary" : "";
  return `<button type="button" class="btn ${cls}" id="${id}">${label}</button>`;
}

function animateNumber(el, target, duration = 700) {
  const start = performance.now();
  function frame(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    // Syne renders "." like a dash at display sizes — set decimals in the UI font instead.
    const [int, dec] = (target * eased).toFixed(1).split(".");
    el.innerHTML = `${int}<span class="score-dec">.${dec}</span>`;
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

let scoreChart, taxChart;

function chartPalette() {
  const grid =
    document.documentElement.getAttribute("data-theme") === "dark"
      ? "rgba(126,140,160,0.14)"
      : "rgba(20,24,31,0.08)";
  return {
    muted: cssVar("--muted", "#6b7585"),
    accent: cssVar("--accent", "#0b6e6a"),
    accentGlow: cssVar("--accent-glow", "rgba(11,110,106,0.16)"),
    blue: cssVar("--blue", "#1f5f8a"),
    orange: cssVar("--orange", "#9a5b12"),
    grid,
  };
}

function drawScore(score) {
  const canvas = document.getElementById("scoreChart");
  if (!canvas || !score?.dimensions) return;
  const pal = chartPalette();
  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(canvas, {
    type: "radar",
    data: {
      labels: Object.keys(score.dimensions).map((k) => k.replace(/_/g, " ")),
      datasets: [
        {
          label: "AI Score",
          data: Object.values(score.dimensions),
          borderColor: pal.accent,
          backgroundColor: pal.accentGlow,
          borderWidth: 2,
          pointBackgroundColor: pal.accent,
          pointRadius: 2.5,
        },
      ],
    },
    options: {
      animation: { duration: 900, easing: "easeOutQuart" },
      plugins: { legend: { display: false } },
      scales: {
        r: {
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: { display: false },
          pointLabels: { color: pal.muted, font: { size: 10, family: "DM Sans" } },
          grid: { color: pal.grid },
          angleLines: { color: pal.grid },
        },
      },
    },
  });
}

function drawTax(tax) {
  const canvas = document.getElementById("taxChart");
  if (!canvas) return;
  const pal = chartPalette();
  if (taxChart) taxChart.destroy();
  taxChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: ["Hit rate %", "Tokens saved /1k", "Cost saved $"],
      datasets: [
        {
          data: [
            (tax.hit_rate || 0) * 100,
            (tax.tokens_saved || 0) / 1000,
            tax.cost_saved_usd || 0,
          ],
          backgroundColor: [pal.accent, pal.blue, pal.orange],
          borderRadius: 3,
          barThickness: 28,
        },
      ],
    },
    options: {
      animation: { duration: 800, easing: "easeOutQuart" },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: pal.muted, font: { size: 11 } }, grid: { display: false } },
        y: { ticks: { color: pal.muted }, grid: { color: pal.grid } },
      },
    },
  });
}

function skeleton() {
  const block = (lines) =>
    `<div class="sk-block">${lines
      .map((w) => `<div class="sk-line ${w}"></div>`)
      .join("")}</div>`;
  return `<div class="skeleton">
    <div class="sk-grid">
      ${block(["w40", "tall"])}
      ${block(["w40", "w70", "w70", "w40"])}
    </div>
    ${block(["w40", "tall"])}
    <div class="sk-grid">
      ${block(["w40", "w70", "w70"])}
      ${block(["w40", "w70", "w70"])}
    </div>
  </div>`;
}

async function renderOverview(payload) {
  const pipes = payload.pipelines || {};
  const m = payload.matrix || {};
  const cells = Object.entries(m)
    .map(
      ([k, v]) => `<div class="health-cell ${v.ok ? "is-ok" : "is-bad"}">
      <div class="health-layer">${k}</div>
      <div class="health-name">${v.name || ""}</div>
      <div class="health-detail">${v.state || v.primary || (v.count != null ? v.count + " workers" : v.ok ? "healthy" : "check")}</div>
    </div>`
    )
    .join("");

  const dims = payload.score?.dimensions || {};
  const dimBars = Object.entries(dims)
    .map(
      ([k, v]) => `<div class="dim-row">
      <span>${k.replace(/_/g, " ")}</span>
      <div class="dim-track"><div class="dim-fill" style="width:${Math.min(100, Number(v) || 0)}%"></div></div>
      <span>${Number(v).toFixed(0)}</span>
    </div>`
    )
    .join("");

  const drifts = (payload.drift?.drifts || []).filter((d) => d.drift);
  const overall = payload.score?.overall ?? 0;
  const driver = payload.driver || {};
  const dogfood = payload.dogfood || {};
  const incidents = payload.incidents?.incidents || [];
  const findings = payload.findings?.findings || [];
  const modeToggle = `<div class="field" style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.75rem">
    ${["ops", "exec", "eng"]
      .map(
        (m) =>
          `<button type="button" class="btn ${viewMode === m ? "" : "secondary"}" data-view-mode="${m}">${m}</button>`
      )
      .join("")}
  </div>`;

  const execPanel =
    viewMode === "exec"
      ? section(
          "Executive",
          `<p class="score-meta">Score, open incidents, compliance findings — business impact.</p>
           <table class="data"><thead><tr><th>Incident</th><th>State</th><th>Tenant</th></tr></thead><tbody>${
             incidents
               .slice(0, 8)
               .map(
                 (i) =>
                   `<tr><td>${escapeHtml(i.title || i.incident_id)}</td><td>${escapeHtml(
                     i.state
                   )}</td><td>${escapeHtml(i.tenant_id)}</td></tr>`
               )
               .join("") || `<tr><td colspan="3" class="empty">No open incidents</td></tr>`
           }</tbody></table>
           <div class="section-head" style="margin-top:1rem"><h2 style="font-size:0.9rem">Compliance findings</h2></div>
           <table class="data"><thead><tr><th>Sev</th><th>Title</th></tr></thead><tbody>${
             findings
               .slice(0, 6)
               .map(
                 (f) =>
                   `<tr><td>${escapeHtml(f.severity)}</td><td>${escapeHtml(f.title)}</td></tr>`
               )
               .join("") || `<tr><td colspan="2" class="empty">Run Admin → Compliance scan</td></tr>`
           }</tbody></table>`,
          "Exec lens",
          0
        )
      : "";

  const engPanel =
    viewMode === "eng"
      ? section(
          "Engineering",
          `<p class="score-meta">Version diff · blast radius · replay live on Trace tab.</p>
           <pre class="surface" style="max-height:220px;overflow:auto;font-size:0.75rem">${escapeHtml(
             JSON.stringify(payload.versionDiff || { note: "snapshot after heartbeats" }, null, 2)
           )}</pre>
           <p style="margin-top:0.5rem">${btn("Refresh version diff", "engDiff", "secondary")}</p>`,
          "Eng lens",
          0
        )
      : "";

  view.className = "view";
  view.innerHTML = `
    ${modeToggle}
    ${execPanel}
    ${engPanel}
    <div class="hero-ops reveal" ${viewMode === "exec" ? 'style="opacity:0.92"' : ""}>
      <div class="score-hero">
        <p class="score-kicker">AI Score ${payload.score?.demo ? "· Demo inputs" : "· Live formula"}</p>
        <div class="score-value" id="scoreNum">0.0</div>
        <p class="score-meta">${payload.score?.formula || "equal_weight_mean(dimensions)"}</p>
        <div class="dim-bars" style="margin-top:1rem;position:relative">${dimBars}</div>
        <div class="score-chart-wrap" style="margin-top:1rem"><canvas id="scoreChart" height="160"></canvas></div>
      </div>
      <div>
        <div class="section-head"><h2>Layer health</h2><span class="hint">L0–L5</span></div>
        <div class="health-ribbon">${cells}</div>
        ${
          drifts.length
            ? `<p class="err" style="margin-top:0.85rem">Policy drift on ${drifts.length} node(s).</p>`
            : `<p class="score-meta" style="margin-top:0.85rem">No policy drift detected.</p>`
        }
      </div>
    </div>

    ${section(
      "Live execution pipeline",
      `<div class="viz-frame" id="vizPipeline"></div>
       <div class="viz-meta"><span>Run <strong id="pipeRunId">—</strong></span><span>Click a stage for detail</span></div>
       <div class="viz-detail" id="pipeDetail">Select a stage on the wire.</div>`,
      "Guard → Ledger → Shine",
      40
    )}

    <div class="grid-2">
      ${section(
        "Fleet topology",
        `<div class="viz-frame" id="vizFleet"></div>
         <div class="viz-detail" id="fleetDetail">Click a node for inventory.</div>`,
        "Live heartbeats",
        80
      )}
      ${section(
        "Token tax & driver",
        `<canvas id="taxChart" height="160"></canvas>
         <p class="score-meta" style="margin-top:0.75rem">Driver p50 ${driver.p50_ms ?? "—"} ms · Dogfood ${
           dogfood.ok ? "ok" : "check"
         }</p>`,
        payload.tax?.demo ? "Demo metrics" : "PrismCache",
        100
      )}
    </div>

    <div class="grid-2">
      ${section(
        "Asset graph map",
        `<div class="viz-frame" id="vizGraph" style="min-height:280px"></div>
         <div class="viz-detail" id="graphDetail">Click an asset for blast-radius context.</div>`,
        `${(pipes.graph?.nodes || []).length} nodes`,
        120
      )}
      ${section(
        "Correction cascade",
        `<div class="viz-frame" id="vizCascade"></div>
         <div class="viz-meta"><span>State <strong>${pipes.cascade?.state || "idle"}</strong></span>
         <span>${pipes.cascade?.cascade_id ? pipes.cascade.cascade_id.slice(0, 12) + "…" : "—"}</span></div>`,
        "Invalidation flow",
        140
      )}
    </div>
  `;

  const numEl = document.getElementById("scoreNum");
  if (numEl) animateNumber(numEl, Number(overall) || 0);
  drawScore(payload.score);
  drawTax(payload.tax || {});

  const runId = pipes.execution?.run_id;
  if (runId) document.getElementById("pipeRunId").textContent = runId;

  requestAnimationFrame(() => {
    if (!window.CCViz) return;
    CCViz.renderExecutionPipeline(document.getElementById("vizPipeline"), pipes.execution, {
      onSelect: (stage) => {
        document.getElementById("pipeDetail").innerHTML = `<strong>${escapeHtml(
          stage.label
        )}</strong> · ${escapeHtml(stage.decision || "—")} ${
          stage.gate ? "· gate " + escapeHtml(stage.gate) : ""
        } · status <code>${escapeHtml(stage.status || "")}</code>`;
      },
    });
    CCViz.renderFleetTopology(document.getElementById("vizFleet"), pipes.fleet, {
      height: 220,
      onSelect: (n) => {
        document.getElementById("fleetDetail").innerHTML = `<strong>${escapeHtml(
          n.label
        )}</strong> · ${escapeHtml(n.role)} · ${n.online ? "online" : "stale"} · zone ${escapeHtml(
          n.zone || "—"
        )} · drops ${n.agent_ledger_dropped_total ?? n.ledger_dropped ?? 0}<br/><span class="score-meta">Products: ${(n.products || []).map(escapeHtml).join(", ") || "—"}</span>`;
      },
    });
    // Live fleet WS (poll fallback already loaded via pipelines)
    try {
      if (!window._ccFleetWs) {
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(
          `${proto}://${location.host}/api/v1/fleet/live?token=${encodeURIComponent(token || "")}`
        );
        window._ccFleetWs = ws;
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === "snapshot" || msg.type === "heartbeat" || msg.type === "join") {
              soft("/api/v1/pipelines/live", null).then((fresh) => {
                if (fresh && window.CCViz) {
                  CCViz.renderFleetTopology(document.getElementById("vizFleet"), fresh.fleet, {
                    height: 220,
                    onSelect: (n) => {
                      document.getElementById("fleetDetail").innerHTML = `<strong>${escapeHtml(
                        n.label
                      )}</strong> · drops ${n.agent_ledger_dropped_total ?? 0}`;
                    },
                  });
                }
              });
            }
          } catch (_) {}
        };
      }
    } catch (_) {}
    CCViz.renderAssetGraph(document.getElementById("vizGraph"), pipes.graph, {
      height: 280,
      onSelect: async (n) => {
        const el = document.getElementById("graphDetail");
        el.textContent = "Loading blast radius…";
        try {
          const br = await j("/api/v1/graph/blast-radius?asset_id=" + encodeURIComponent(n.id));
          el.innerHTML = `<strong>${escapeHtml(n.label)}</strong> (${escapeHtml(n.kind)}) · impacts ${
            (br.impacts || []).length
          } · depends_on ${(br.depends_on || []).length}`;
        } catch (e) {
          el.textContent = String(e.message || e);
        }
      },
    });
    CCViz.renderCascade(document.getElementById("vizCascade"), pipes.cascade);
  });

  document.querySelectorAll("[data-view-mode]").forEach((el) => {
    el.onclick = () => setViewMode(el.getAttribute("data-view-mode"));
  });
  const engBtn = document.getElementById("engDiff");
  if (engBtn) {
    engBtn.onclick = async () => {
      const diff = await soft("/api/v1/fleet/version-diff?tenant_id=default", {});
      payload.versionDiff = diff;
      lastRender = () => renderOverview(payload);
      await renderOverview(payload);
    };
  }
}

async function renderTrace(payload) {
  actions.innerHTML = btn("Seed demo trace", "seedTrace", "secondary") + btn("Replay selected", "replayTrace");
  const traces = payload.traces || [];
  const pipes = payload.pipelines || {};
  view.innerHTML = `
    ${section(
      "Animated wire",
      `<div class="viz-frame" id="vizPipeline"></div>
       <div class="viz-detail" id="pipeDetail">Live from latest ledger stitch</div>`,
      "Data-driven",
      0
    )}
    <div class="grid-2">
      ${section(
        "Runs",
        `<table class="data"><thead><tr><th></th><th>Run</th><th>Created</th></tr></thead><tbody>${
          traces
            .map(
              (t, i) => `<tr>
            <td><input type="radio" name="run" value="${t.run_id}" ${i === 0 ? "checked" : ""}></td>
            <td><code>${t.run_id}</code></td>
            <td>${new Date((t.created_at || 0) * 1000).toLocaleString()}</td>
          </tr>`
            )
            .join("") || `<tr><td colspan="3" class="empty">No traces yet</td></tr>`
        }</tbody></table>`,
        "Ledger store",
        40
      )}
      ${section("Stage list", `<div class="timeline" id="timeline"><p class="empty">Select a run</p></div>`, "Guard → Ledger → Shine", 80)}
    </div>
  `;

  requestAnimationFrame(() => {
    window.CCViz?.renderExecutionPipeline(document.getElementById("vizPipeline"), pipes.execution, {
      onSelect: (s) => {
        document.getElementById("pipeDetail").textContent = `${s.label}: ${s.decision || s.status}`;
      },
    });
  });

  async function showRun(runId) {
    const tr = await j("/api/v1/traces/" + runId);
    const stages = tr.wire?.stages || [];
    document.getElementById("timeline").innerHTML =
      stages
        .map(
          (s) => `<div class="timeline-step">
        <div class="timeline-stage">${s.stage}</div>
        <div class="timeline-detail">${s.decision || s.hop || s.kind || ""}${
            s.resolution_gate ? " · gate " + s.resolution_gate : ""
          }</div>
      </div>`
        )
        .join("") || `<p class="empty">Empty wire</p>`;
    window.CCViz?.renderExecutionPipeline(
      document.getElementById("vizPipeline"),
      {
        stages: stages.map((s, i) => ({
          id: s.stage || "s" + i,
          label: (s.stage || "step").replace(/^./, (c) => c.toUpperCase()),
          decision: s.decision || s.hop || s.kind,
          gate: s.resolution_gate,
          status: s.decision === "block" ? "bad" : "ok",
        })),
      },
      {
        onSelect: (st) => {
          document.getElementById("pipeDetail").textContent = `${st.label}: ${st.decision || ""}`;
        },
      }
    );
  }

  const first = traces[0]?.run_id;
  if (first) await showRun(first);
  document.querySelectorAll('input[name="run"]').forEach((r) =>
    r.addEventListener("change", () => showRun(r.value))
  );
  document.getElementById("seedTrace").onclick = async () => {
    await j("/api/v1/traces/seed", { method: "POST", body: JSON.stringify({ tenant_id: "default" }) });
    location.reload();
  };
  document.getElementById("replayTrace").onclick = async () => {
    const runId = document.querySelector('input[name="run"]:checked')?.value;
    if (!runId) return;
    const r = await j("/api/v1/traces/" + runId + "/replay", { method: "POST", body: "{}" });
    const tl = document.getElementById("timeline");
    tl.insertAdjacentHTML(
      "beforeend",
      `<div class="surface" style="margin-top:1rem"><strong>Replay</strong> · LLM calls: ${r.llm_calls} · ${
        r.ok ? status(true, "zero-token ok") : status(false, "failed")
      }</div>`
    );
  };
}

async function renderTaxonomy(payload) {
  const tenantId =
    payload.tenantId ||
    (payload.partitions?.partitions || []).find((p) => p.tenant_id)?.tenant_id ||
    "default";
  const partsList = payload.partitions?.partitions || [];
  const defaultPartition =
    partsList.find((p) => String(p.partition || "").includes("clinical"))?.partition ||
    partsList[0]?.partition ||
    "kb_markdown";

  actions.innerHTML =
    btn("Reindex", "doReindex", "secondary") +
    btn("Warm partition", "doWarm") +
    btn("Refresh", "doTaxRefresh", "secondary");

  const cats = (payload.tree?.categories || [])
    .map((c) => `<tr><td>${escapeHtml(c.slug)}</td><td>${escapeHtml(c.label || "—")}</td></tr>`)
    .join("");
  const parts = partsList
    .map(
      (p) => `<tr>
      <td>${escapeHtml(p.partition)}</td>
      <td><strong>${escapeHtml(String(p.version ?? "—"))}</strong></td>
      <td>${escapeHtml(p.status || "ready")}</td>
      <td>${escapeHtml(p.tenant_id || "")}</td>
    </tr>`
    )
    .join("");
  const decay = (payload.health?.decay || [])
    .map((d) => {
      const stale = Number(d.staleness) || 0;
      return `<tr><td>${escapeHtml(d.slug)}</td><td>${stale.toFixed(2)}</td><td>${
        stale > 0.3 ? status(false, "stale") : status(true, "fresh")
      }</td></tr>`;
    })
    .join("");

  const partOptions = partsList
    .map(
      (p) =>
        `<option value="${escapeHtml(p.partition)}" ${
          p.partition === defaultPartition ? "selected" : ""
        }>${escapeHtml(p.partition)} (v${escapeHtml(String(p.version ?? "?"))})</option>`
    )
    .join("");

  view.innerHTML = `
    <div class="tax-toolbar surface" style="margin-bottom:1rem;padding:0.85rem 1rem">
      <div class="tax-toolbar-row">
        <label>Tenant
          <select id="taxTenant">
            <option value="aurora-health" ${tenantId === "aurora-health" ? "selected" : ""}>aurora-health</option>
            <option value="aurora-pharmacy" ${tenantId === "aurora-pharmacy" ? "selected" : ""}>aurora-pharmacy</option>
            <option value="default" ${tenantId === "default" ? "selected" : ""}>default</option>
          </select>
        </label>
        <label>Partition
          <select id="taxPartition">${
            partOptions || `<option value="kb_markdown">kb_markdown</option>`
          }</select>
        </label>
        <label class="tax-search">Search term
          <input id="taxQuery" type="search" placeholder="med recon, allergy, insulin…" />
        </label>
        <button type="button" class="btn" id="doTaxSearch">Search + embed</button>
      </div>
      <div id="taxJobStatus" class="score-meta" style="margin-top:0.65rem" role="status">
        Search runs PrismRAG embed retrieval, shows related words, and lets admins overwrite a chunk online.
      </div>
    </div>
    <div class="grid-2">
      ${section(
        "Category tree",
        `<table class="data"><thead><tr><th>Slug</th><th>Label</th></tr></thead><tbody>${
          cats || `<tr><td colspan="2" class="empty">Empty</td></tr>`
        }</tbody></table>`,
        escapeHtml(tenantId),
        0
      )}
      ${section(
        "Partitions",
        `<table class="data"><thead><tr><th>Partition</th><th>Ver</th><th>Status</th><th>Tenant</th></tr></thead><tbody>${
          parts || `<tr><td colspan="4" class="empty">No partitions</td></tr>`
        }</tbody></table>`,
        payload.tree?.demo || payload.health?.demo ? "DEMO NullRAG partitions" : "live",
        60
      )}
    </div>
    ${section(
      "Chunk health",
      `<table class="data"><thead><tr><th>Category</th><th>Staleness</th><th>State</th></tr></thead><tbody>${
        decay || `<tr><td colspan="3" class="empty">No decay data</td></tr>`
      }</tbody></table>
       <p class="score-meta" style="margin-top:0.75rem">Bleed risk: ${
         payload.health?.bleed_risk ?? "n/a"
       }</p>`,
      "PrismRAG",
      80
    )}
    ${section(
      "Search · related embeddings · overwrite",
      `<div id="taxSearchHits"><p class="empty">Search a term to see hits, related words from the embedding/community graph, and edit a chunk online.</p></div>`,
      "admin overwrite",
      120
    )}
  `;

  async function reloadTaxonomy(nextTenant) {
    const tid = nextTenant || document.getElementById("taxTenant")?.value || tenantId;
    const [tree, partitions, health] = await Promise.all([
      soft(`/api/v1/taxonomy/tree?tenant_id=${encodeURIComponent(tid)}`, { categories: [] }),
      soft(`/api/v1/taxonomy/partitions?tenant_id=${encodeURIComponent(tid)}`, { partitions: [] }),
      soft(`/api/v1/taxonomy/chunks/health?tenant_id=${encodeURIComponent(tid)}`, { decay: [] }),
    ]);
    const next = { tree, partitions, health, tenantId: tid };
    lastRender = () => renderTaxonomy(next);
    await renderTaxonomy(next);
  }

  async function pollJob(jobId, label) {
    const statusEl = document.getElementById("taxJobStatus");
    for (let i = 0; i < 40; i++) {
      const job = await j(`/api/v1/jobs/${jobId}`);
      if (statusEl) {
        statusEl.innerHTML = `${escapeHtml(label)} · <code>${escapeHtml(jobId)}</code> · ${status(
          job.state === "completed",
          job.state
        )}${job.error ? ` · ${escapeHtml(String(job.error))}` : ""}`;
      }
      if (out) out.textContent = JSON.stringify(job, null, 2);
      if (job.state === "completed" || job.state === "failed") return job;
      await new Promise((r) => setTimeout(r, 200));
    }
    return null;
  }

  function renderSearchPanel(r) {
    const hitsEl = document.getElementById("taxSearchHits");
    if (!hitsEl) return;
    const resultRows = r.results || [];
    const related = (r.related_terms || [])
      .map(
        (t) =>
          `<button type="button" class="rel-chip" data-term="${escapeHtml(t.term)}" title="${escapeHtml(
            t.relation || t.source || ""
          )}">${escapeHtml(t.term)}</button>`
      )
      .join("");
    const rows = resultRows
      .map((h, i) => {
        const ref = h.chunk_ref || h.category_slug || `hit-${i}`;
        const text = h.chunk_text || h.text || "";
        return `<tr>
          <td><code>${escapeHtml(ref)}</code></td>
          <td>${escapeHtml(h.category_slug || "")}</td>
          <td>${escapeHtml(text)}</td>
          <td>${escapeHtml(String(h.score ?? ""))}</td>
          <td><button type="button" class="btn secondary tax-pick" data-i="${i}">Edit</button></td>
        </tr>`;
      })
      .join("");
    hitsEl.innerHTML = `
      <p class="score-meta">Engine <strong>${escapeHtml(r.engine || "?")}</strong>
        · mode <strong>${escapeHtml(r.retrieval_mode || "?")}</strong>
        ${r.demo ? " · DEMO fallback" : " · live PrismRAG"}
        · query <code>${escapeHtml(r.query || "")}</code></p>
      <div class="rel-wrap">
        <div class="section-head"><h2 style="font-size:0.9rem;margin:0">Related words (embed / community)</h2></div>
        <div class="rel-chips">${related || `<span class="empty">No related terms</span>`}</div>
        <p class="score-meta">Click a related word to re-search. Hover for why it is related.</p>
      </div>
      <table class="data" style="margin-top:0.85rem">
        <thead><tr><th>Chunk ref</th><th>Category</th><th>Text</th><th>Score</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5" class="empty">No hits</td></tr>`}</tbody>
      </table>
      <div id="taxOverwrite" class="tax-overwrite surface" hidden style="margin-top:1rem;padding:0.9rem 1rem">
        <div class="section-head"><h2 style="font-size:0.95rem;margin:0">Overwrite chunk online</h2>
          <span class="hint">PrismRAG append_chunks upsert</span></div>
        <label class="tax-ow-label">Chunk ref <input id="owRef" readonly /></label>
        <label class="tax-ow-label">Category <input id="owCat" /></label>
        <label class="tax-ow-label">Chunk text
          <textarea id="owText" rows="5"></textarea>
        </label>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.55rem">
          <button type="button" class="btn" id="owSave">Save overwrite</button>
          <button type="button" class="btn secondary" id="owCancel">Cancel</button>
        </div>
        <p id="owStatus" class="score-meta" style="margin-top:0.55rem"></p>
      </div>`;

    hitsEl.querySelectorAll(".rel-chip").forEach((chip) => {
      chip.addEventListener("click", async () => {
        const term = chip.getAttribute("data-term") || "";
        const input = document.getElementById("taxQuery");
        if (input) input.value = term;
        await runTaxSearch(term);
      });
    });

    hitsEl.querySelectorAll(".tax-pick").forEach((b) => {
      b.addEventListener("click", () => {
        const i = Number(b.getAttribute("data-i") || 0);
        const h = resultRows[i] || {};
        const panel = document.getElementById("taxOverwrite");
        if (!panel) return;
        document.getElementById("owRef").value = h.chunk_ref || h.category_slug || "";
        document.getElementById("owCat").value = h.category_slug || "";
        document.getElementById("owText").value = h.chunk_text || h.text || "";
        document.getElementById("owStatus").textContent = "";
        panel.hidden = false;
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });

    document.getElementById("owCancel")?.addEventListener("click", () => {
      const panel = document.getElementById("taxOverwrite");
      if (panel) panel.hidden = true;
    });

    document.getElementById("owSave")?.addEventListener("click", async () => {
      const statusEl = document.getElementById("owStatus");
      const tid = document.getElementById("taxTenant")?.value || tenantId;
      const partition = document.getElementById("taxPartition")?.value || defaultPartition;
      try {
        if (statusEl) statusEl.textContent = "Saving overwrite via PrismRAG…";
        const saved = await j("/api/v1/taxonomy/chunks/overwrite", {
          method: "POST",
          body: JSON.stringify({
            tenant_id: tid,
            chunk_ref: document.getElementById("owRef")?.value || "",
            text: document.getElementById("owText")?.value || "",
            category_slug: document.getElementById("owCat")?.value || null,
            partition,
          }),
        });
        if (statusEl) {
          statusEl.innerHTML = `${status(true, "overwritten")} · ref <code>${escapeHtml(
            saved.chunk_ref || ""
          )}</code> · quality ${escapeHtml(String(saved.quality_score ?? "n/a"))}
            · embed dim ${escapeHtml(String(saved.embedding_dim ?? 0))}`;
        }
        if (out) out.textContent = JSON.stringify(saved, null, 2);
        await runTaxSearch(document.getElementById("taxQuery")?.value || saved.chunk_ref);
      } catch (err) {
        if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
      }
    });
  }

  async function runTaxSearch(forcedQuery) {
    const hitsEl = document.getElementById("taxSearchHits");
    const statusEl = document.getElementById("taxJobStatus");
    const tid = document.getElementById("taxTenant")?.value || tenantId;
    const query = forcedQuery != null ? forcedQuery : document.getElementById("taxQuery")?.value || "";
    try {
      if (statusEl) statusEl.textContent = `Searching “${query}” with PrismRAG…`;
      const r = await j("/api/v1/taxonomy/search", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tid, query, top_k: 8 }),
      });
      if (out) out.textContent = JSON.stringify(r, null, 2);
      renderSearchPanel(r);
      if (statusEl) {
        statusEl.innerHTML = `Search done · ${escapeHtml(r.engine || "")} · ${escapeHtml(
          r.retrieval_mode || ""
        )} · ${(r.results || []).length} hits · ${(r.related_terms || []).length} related terms`;
      }
    } catch (err) {
      if (hitsEl) hitsEl.innerHTML = `<p class="err">${escapeHtml(err.message || err)}</p>`;
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  }

  document.getElementById("taxTenant")?.addEventListener("change", async (e) => {
    await reloadTaxonomy(e.target.value);
  });

  document.getElementById("doTaxRefresh")?.addEventListener("click", async () => {
    await reloadTaxonomy();
  });

  document.getElementById("doReindex").onclick = async () => {
    const statusEl = document.getElementById("taxJobStatus");
    const tid = document.getElementById("taxTenant")?.value || tenantId;
    try {
      if (statusEl) statusEl.textContent = "Queuing reindex…";
      const queued = await j("/api/v1/jobs/reindex", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tid }),
      });
      await pollJob(queued.job_id, "Reindex");
      await reloadTaxonomy(tid);
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  };

  document.getElementById("doWarm").onclick = async () => {
    const statusEl = document.getElementById("taxJobStatus");
    const tid = document.getElementById("taxTenant")?.value || tenantId;
    const partition = document.getElementById("taxPartition")?.value || defaultPartition;
    try {
      if (statusEl) statusEl.textContent = `Queuing warm for ${partition}…`;
      const queued = await j("/api/v1/jobs/warm-partition", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tid, partition }),
      });
      await pollJob(queued.job_id, `Warm ${partition}`);
      await reloadTaxonomy(tid);
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  };

  document.getElementById("doTaxSearch")?.addEventListener("click", () => runTaxSearch());
  document.getElementById("taxQuery")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runTaxSearch();
    }
  });
}

async function renderCortex(payload) {
  const snap = payload.snapshot || {};
  const tenantId = payload.tenantId || snap.tenant_id || "aurora-health";
  actions.innerHTML =
    btn("Digest", "doCxDigest") +
    btn("Recall", "doCxRecall", "secondary") +
    btn("Sleep", "doCxSleep", "secondary") +
    btn("Refresh", "doCxRefresh", "secondary");

  const activity = (snap.activity || [])
    .map((a) => {
      const when = a.ts ? new Date(a.ts * 1000).toLocaleTimeString() : "";
      const detail =
        a.text || a.query || a.subject || a.outcome || a.consolidated || "";
      return `<tr>
        <td>${escapeHtml(when)}</td>
        <td><code>${escapeHtml(a.kind || "")}</code></td>
        <td>${escapeHtml(String(detail).slice(0, 140))}</td>
        <td>${escapeHtml(String(a.version ?? a.cache_hit ?? ""))}</td>
      </tr>`;
    })
    .join("");

  const chunks = (snap.chunks || [])
    .map(
      (c) => `<tr>
      <td><code>${escapeHtml(c.chunk_ref || c.id || "")}</code></td>
      <td>${escapeHtml(c.label || c.chunk_text || "")}</td>
      <td>${escapeHtml(c.band || "")}</td>
      <td>${escapeHtml(String(c.embedding_dim ?? 0))}</td>
      <td>${escapeHtml(String(c.confidence ?? ""))}</td>
    </tr>`
    )
    .join("");

  const facts = (snap.facts || [])
    .map(
      (f) => `<tr>
      <td>${escapeHtml(f.fact || `${f.src_label} ${f.relation} ${f.dst_label}`)}</td>
      <td>${escapeHtml(String(f.weight ?? ""))}</td>
      <td>${f.current === false ? status(false, "superseded") : status(true, "active")}</td>
    </tr>`
    )
    .join("");

  const superseded = (snap.superseded || [])
    .slice(0, 8)
    .map(
      (f) =>
        `<tr><td>${escapeHtml(f.fact || "")}</td><td>${escapeHtml(
          f.valid_to || ""
        )}</td></tr>`
    )
    .join("");

  const conflicts = (snap.conflicts || [])
    .map(
      (c) => `<tr>
      <td>${escapeHtml(c.subject || c.fact || c.id || "")}</td>
      <td>${escapeHtml(c.relation || "is")}</td>
      <td>${escapeHtml(String(c.old_value || c.old || ""))} → ${escapeHtml(
        String(c.new_value || c.new || "")
      )}</td>
      <td><button type="button" class="btn secondary cx-resolve" data-subject="${escapeHtml(
        c.subject || c.fact || ""
      )}" data-relation="${escapeHtml(c.relation || "is")}" data-new="${escapeHtml(
        String(c.new_value || c.new || "")
      )}">Keep new</button></td>
    </tr>`
    )
    .join("");

  view.innerHTML = `
    <div class="tax-toolbar surface" style="margin-bottom:1rem;padding:0.85rem 1rem">
      <div class="tax-toolbar-row">
        <label>Tenant
          <select id="cxTenant">
            <option value="aurora-health" ${tenantId === "aurora-health" ? "selected" : ""}>aurora-health</option>
            <option value="aurora-pharmacy" ${tenantId === "aurora-pharmacy" ? "selected" : ""}>aurora-pharmacy</option>
            <option value="default" ${tenantId === "default" ? "selected" : ""}>default</option>
          </select>
        </label>
        <label class="tax-search">Digest text
          <input id="cxDigest" type="text" placeholder="Medication recon policy is check allergies first." />
        </label>
        <label class="tax-search">Recall / explain
          <input id="cxQuery" type="search" placeholder="What is medication recon policy?" />
        </label>
      </div>
      <div id="cxStatus" class="score-meta" style="margin-top:0.65rem" role="status">
        Engine <strong>${escapeHtml(snap.engine || "?")}</strong>
        · version <strong>${escapeHtml(String(snap.version ?? "—"))}</strong>
        · nodes ${escapeHtml(String(snap.node_count ?? (snap.chunks || []).length))}
        · facts ${escapeHtml(String(snap.current_fact_count ?? (snap.facts || []).length))}
        ${snap.demo ? " · fallback" : " · live PrismCortex"}
      </div>
    </div>
    <div class="grid-2">
      ${section(
        "Activity",
        `<table class="data"><thead><tr><th>When</th><th>Kind</th><th>Detail</th><th>Meta</th></tr></thead>
         <tbody>${activity || `<tr><td colspan="4" class="empty">No activity yet — digest a fact</td></tr>`}</tbody></table>`,
        "MemoryEvent + console",
        0
      )}
      ${section(
        "Memory chunks (graph nodes)",
        `<table class="data"><thead><tr><th>Ref</th><th>Label</th><th>Band</th><th>Embed</th><th>Conf</th></tr></thead>
         <tbody>${chunks || `<tr><td colspan="5" class="empty">No chunks</td></tr>`}</tbody></table>`,
        "bitemporal",
        40
      )}
    </div>
    <div class="grid-2">
      ${section(
        "Current facts",
        `<table class="data"><thead><tr><th>Fact</th><th>Weight</th><th>State</th></tr></thead>
         <tbody>${facts || `<tr><td colspan="3" class="empty">No facts</td></tr>`}</tbody></table>
         ${
           superseded
             ? `<p class="score-meta" style="margin-top:0.75rem">Superseded</p>
                <table class="data"><thead><tr><th>Fact</th><th>Valid to</th></tr></thead><tbody>${superseded}</tbody></table>`
             : ""
         }`,
        "edges",
        80
      )}
      ${section(
        "Conflicts",
        `<table class="data"><thead><tr><th>Subject</th><th>Rel</th><th>Change</th><th></th></tr></thead>
         <tbody>${conflicts || `<tr><td colspan="4" class="empty">None open</td></tr>`}</tbody></table>
         <div id="cxCascade" style="margin-top:0.75rem"></div>
         <div id="cxRecallOut" class="surface" style="margin-top:0.75rem;padding:0.75rem" hidden></div>`,
        "resolve → cascade",
        100
      )}
    </div>
  `;

  async function reloadCortex(nextTenant) {
    const tid = nextTenant || document.getElementById("cxTenant")?.value || tenantId;
    const snapshot = await soft(
      `/api/v1/cortex/snapshot?tenant_id=${encodeURIComponent(tid)}`,
      { activity: [], chunks: [], facts: [], conflicts: [], engine: "null" }
    );
    const next = { snapshot, tenantId: tid };
    lastRender = () => renderCortex(next);
    await renderCortex(next);
  }

  document.getElementById("cxTenant")?.addEventListener("change", async (e) => {
    await reloadCortex(e.target.value);
  });
  document.getElementById("doCxRefresh")?.addEventListener("click", () => reloadCortex());

  document.getElementById("doCxDigest")?.addEventListener("click", async () => {
    const statusEl = document.getElementById("cxStatus");
    const tid = document.getElementById("cxTenant")?.value || tenantId;
    const text = document.getElementById("cxDigest")?.value || "";
    try {
      if (statusEl) statusEl.textContent = "Digesting…";
      const r = await j("/api/v1/cortex/digest", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tid, text }),
      });
      if (out) out.textContent = JSON.stringify(r, null, 2);
      await reloadCortex(tid);
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  });

  document.getElementById("doCxRecall")?.addEventListener("click", async () => {
    const statusEl = document.getElementById("cxStatus");
    const panel = document.getElementById("cxRecallOut");
    const tid = document.getElementById("cxTenant")?.value || tenantId;
    const query = document.getElementById("cxQuery")?.value || "";
    try {
      const [rec, exp] = await Promise.all([
        j("/api/v1/cortex/recall", {
          method: "POST",
          body: JSON.stringify({ tenant_id: tid, query }),
        }),
        j("/api/v1/cortex/explain", {
          method: "POST",
          body: JSON.stringify({ tenant_id: tid, query }),
        }),
      ]);
      if (out) out.textContent = JSON.stringify({ recall: rec, explain: exp }, null, 2);
      if (panel) {
        panel.hidden = false;
        const ev = (exp.evidence || [])
          .map((e) => `<li>${escapeHtml(e.fact || "")} <span class="hint">conf ${escapeHtml(
            String(e.confidence ?? "")
          )}</span></li>`)
          .join("");
        panel.innerHTML = `<strong>Recall</strong>
          <p>${escapeHtml(rec.answer || "")}</p>
          <p class="score-meta">cache=${escapeHtml(String(rec.cache_hit))} · conf=${escapeHtml(
            String(rec.confidence)
          )} · v${escapeHtml(String(rec.version))}</p>
          <strong>Explain evidence</strong>
          <ul style="margin:0.4rem 0 0;padding-left:1.1rem">${ev || "<li class='empty'>none</li>"}</ul>`;
      }
      if (statusEl) {
        statusEl.innerHTML = `Recall ${status(true, "ok")} · cache_hit=${escapeHtml(
          String(rec.cache_hit)
        )}`;
      }
      // refresh activity without full wipe of recall panel content after short delay
      const snap = await soft(
        `/api/v1/cortex/snapshot?tenant_id=${encodeURIComponent(tid)}`,
        {}
      );
      payload.snapshot = snap;
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  });

  document.getElementById("doCxSleep")?.addEventListener("click", async () => {
    const statusEl = document.getElementById("cxStatus");
    const tid = document.getElementById("cxTenant")?.value || tenantId;
    try {
      const r = await j("/api/v1/cortex/sleep", {
        method: "POST",
        body: JSON.stringify({ tenant_id: tid }),
      });
      if (out) out.textContent = JSON.stringify(r, null, 2);
      await reloadCortex(tid);
      if (statusEl) {
        statusEl.innerHTML = `Sleep ${status(true, "ok")} · consolidated ${escapeHtml(
          String(r.consolidated ?? 0)
        )}`;
      }
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span class="err">${escapeHtml(err.message || err)}</span>`;
    }
  });

  document.querySelectorAll(".cx-resolve").forEach((b) => {
    b.addEventListener("click", async () => {
      const tid = document.getElementById("cxTenant")?.value || tenantId;
      const panel = document.getElementById("cxCascade");
      try {
        const r = await j("/api/v1/cortex/conflicts/resolve", {
          method: "POST",
          body: JSON.stringify({
            tenant_id: tid,
            subject: b.getAttribute("data-subject"),
            relation: b.getAttribute("data-relation") || "is",
            chosen_value: b.getAttribute("data-new"),
          }),
        });
        if (panel) {
          panel.innerHTML = `<div class="surface" style="padding:0.75rem">
            <div class="section-head"><h2 style="font-size:0.95rem;margin:0">Cascade</h2>${status(
              true,
              "queued"
            )}</div>
            <code>${escapeHtml(r.cascade?.cascade_id || "")}</code>
          </div>`;
        }
        await reloadCortex(tid);
      } catch (err) {
        if (panel) panel.innerHTML = `<p class="err">${escapeHtml(err.message || err)}</p>`;
      }
    });
  });
}

async function renderMemory(payload) {
  // Back-compat if anything still calls memory — redirect render to Cortex shape
  return renderCortex({
    snapshot: {
      facts: (payload.facts?.facts || []).map((f) => ({
        fact: `${f.fact} is ${f.value}`,
        current: f.status === "active",
        weight: 1,
      })),
      conflicts: payload.conflicts?.conflicts || [],
      activity: [],
      chunks: [],
      engine: "null",
      demo: true,
    },
    tenantId: "default",
  });
}

async function renderGuard(payload) {
  const pol = payload.policy?.policy || {};
  actions.innerHTML = btn("Save policy", "savePol") + btn("Shadow compare", "shadowCmp", "secondary");
  view.innerHTML = `
    <div class="grid-2">
      ${section(
        "Policy Studio",
        `<div class="field"><label>Ingress profile</label><input id="ingress_profile" value="${pol.ingress_profile || "web_chat"}" /></div>
         <div class="field"><label>Ingress use ONNX</label>
           <select id="ingress_use_onnx">
             <option value="false" ${!pol.ingress_use_onnx ? "selected" : ""}>false</option>
             <option value="true" ${pol.ingress_use_onnx ? "selected" : ""}>true</option>
           </select>
         </div>
         <div class="field"><label>Shadow profile</label><input id="shadow_profile" value="${pol.shadow_profile || "light"}" /></div>
         <div class="field"><label>Shadow enabled</label>
           <select id="shadow_enabled">
             <option value="true" ${pol.shadow_enabled !== false ? "selected" : ""}>true</option>
             <option value="false">false</option>
           </select>
         </div>
         <div class="field"><label>Artifact ID (domain_pilot)</label><input id="artifact_id" value="${pol.artifact_id || ""}" /></div>
         <div class="field"><label>Recommended preset</label><input id="recommended_preset" value="${pol.recommended_preset || "finance_hub"}" /></div>
         <p id="polErr" class="err"></p>`,
        "finance_hub → web_chat",
        0
      )}
      ${section(
        "Recent decisions",
        `<table class="data"><thead><tr><th>Decision</th><th>Gate</th><th>Preview</th></tr></thead><tbody>${
          (payload.logs?.logs || [])
            .map(
              (l) =>
                `<tr><td>${l.decision}</td><td>${l.resolution_gate}</td><td>${l.prompt_preview || ""}</td></tr>`
            )
            .join("")
        }</tbody></table><div id="shadowOut" style="margin-top:1rem"></div>`,
        "PrismGuard",
        60
      )}
    </div>
  `;

  document.getElementById("savePol").onclick = async () => {
    const policy = {
      ingress_profile: document.getElementById("ingress_profile").value,
      ingress_use_onnx: document.getElementById("ingress_use_onnx").value === "true",
      shadow_profile: document.getElementById("shadow_profile").value,
      shadow_enabled: document.getElementById("shadow_enabled").value === "true",
      artifact_id: document.getElementById("artifact_id").value || undefined,
      recommended_preset: document.getElementById("recommended_preset").value,
    };
    try {
      const r = await j("/api/v1/guard/policy", {
        method: "PUT",
        body: JSON.stringify({ tenant_id: "default", policy }),
      });
      document.getElementById("polErr").textContent = "";
      out.textContent = JSON.stringify(r, null, 2);
    } catch (e) {
      document.getElementById("polErr").textContent = String(e.message || e);
    }
  };
  document.getElementById("shadowCmp").onclick = async () => {
    const r = await j("/api/v1/guard/shadow/compare");
    document.getElementById("shadowOut").innerHTML = `<div class="surface">
      <strong>Agree rate</strong> ${(Number(r.agree_rate || 0) * 100).toFixed(1)}%
      ${r.demo ? status(false, "demo") : status(true, "live")}
    </div>`;
  };
}

async function renderAdmin(payload) {
  actions.innerHTML =
    btn("Create join token", "mkToken") +
    btn("Compliance scan", "cmpScan", "secondary") +
    btn("SOC2 export", "soc2", "secondary");
  const lic = payload.license || {};
  const doctor = payload.doctor || {};
  const auth = payload.auth || {};
  const recs = payload.recommendations?.recommendations || [];
  const assets = payload.graph?.assets || [];
  const pins = (doctor.pins?.pins || []).slice(0, 8);
  const pg = doctor.postgres;
  const pgLabel = !pg ? "not configured" : pg.ok ? "connected" : "error";
  const incidents = payload.incidents?.incidents || [];
  const findings = payload.findings?.findings || [];
  const ep = payload.enterprise?.policies || [];

  view.innerHTML = `
    <div class="grid-2">
      ${section(
        "License",
        `<p style="margin:0 0 0.5rem"><strong style="font-family:var(--font-display);font-size:1.35rem;letter-spacing:-0.03em">${
          lic.state || "—"
        }</strong> ${lic.state === "valid" ? status(true, "valid") : status(false, lic.state || "check")}</p>
         <p class="score-meta">${lic.message || ""}</p>
         <p class="score-meta">Grace remaining: ${lic.grace_remaining_seconds ?? "n/a"}s</p>
         <p style="margin-top:0.85rem"><a class="rail-support" href="${lic.portal_url || "#"}" target="_blank" rel="noreferrer">Open renewal portal</a></p>
         <p class="score-meta" style="margin-top:0.5rem">Online check: ${
           lic.online_check?.enabled
             ? `every ${lic.online_check.interval_days || 14}d · last ${
                 lic.online_check.last?.status || lic.online_check.last?.last_error || "not run"
               }`
             : "disabled (air-gap / demo)"
         }</p>
         <table class="data" style="margin-top:1rem"><tbody>
           <tr><td>Tier</td><td>${lic.claims?.tier || "—"}</td></tr>
           <tr><td>Max nodes</td><td>${lic.claims?.max_nodes ?? "—"}</td></tr>
           <tr><td>Org</td><td>${lic.claims?.sub || "—"}</td></tr>
         </tbody></table>
         <div class="field" style="margin-top:1rem"><label>Install license key</label>
           <textarea id="licKey" rows="3" placeholder="Paste license JWT" style="width:100%;font-family:var(--font-mono);font-size:0.75rem"></textarea>
         </div>
         <p style="margin-top:0.5rem">${btn("Install license", "installLic", "secondary")} ${btn(
           "Online check",
           "onlineLic",
           "secondary"
         )}</p>`,
        "Offline verify + optional Side 1",
        0
      )}
      ${section(
        "Doctor",
        `<table class="data"><tbody>
          <tr><td>Transport</td><td>${doctor.transport_primary || "—"}</td></tr>
          <tr><td>Demo mode</td><td>${doctor.demo_mode ? status(false, "on") : status(true, "off")}</td></tr>
          <tr><td>Fleet nodes</td><td>${doctor.fleet_nodes ?? "—"}</td></tr>
          <tr><td>SQLite</td><td><code>${doctor.sqlite || "—"}</code></td></tr>
          <tr><td>Postgres audit</td><td>${pg ? status(!!pg.ok, pgLabel) : status(true, pgLabel)}</td></tr>
          <tr><td>OIDC</td><td>${doctor.oidc_enabled ? status(true, "enabled") : status(true, "token only")}</td></tr>
        </tbody></table>
        <div class="section-head" style="margin-top:1rem"><h2 style="font-size:0.9rem">Pin floors</h2></div>
        ${
          doctor.install_hint
            ? `<p class="score-meta" style="margin:0.5rem 0">Install: <code>${doctor.install_hint}</code></p>`
            : ""
        }
        <table class="data"><thead><tr><th>Package</th><th>Floor</th><th>Installed</th><th>Tier</th><th>Status</th></tr></thead><tbody>${
          (doctor.pins?.pins || [])
            .map(
              (p) =>
                `<tr><td>${p.package}</td><td>${p.floor}</td><td>${p.installed || "—"}</td><td>${
                  p.tier || "—"
                }</td><td>${
                  p.ok
                    ? status(true, "ok")
                    : status(p.tier !== "core", p.status || "missing")
                }</td></tr>`
            )
            .join("") || `<tr><td colspan="5" class="empty">No pin report</td></tr>`
        }</tbody></table>
        ${
          doctor.taxonomy_packs
            ? `<p class="score-meta" style="margin-top:0.75rem">Taxonomy packs: ${
                doctor.taxonomy_packs.ready
                  ? status(true, "ready")
                  : status(false, "not ready")
              } ${
                doctor.taxonomy_packs.install_hint
                  ? `· <code>${doctor.taxonomy_packs.install_hint}</code>`
                  : ""
              }</p>`
            : ""
        }
        <table class="data" style="margin-top:0.75rem"><tbody>
          <tr><td>Package version</td><td><code>${doctor.version || "—"}</code></td></tr>
        </tbody></table>`,
        "Mother health",
        60
      )}
    </div>
    <div class="grid-2">
      ${section(
        "Auth",
        `<table class="data"><tbody>
          <tr><td>Local token</td><td>${auth.local_token ? status(true, "yes") : "—"}</td></tr>
          <tr><td>OIDC</td><td>${auth.oidc_enabled ? status(true, "enabled") : status(true, "off")}</td></tr>
          <tr><td>Issuer</td><td><code>${auth.oidc_issuer || "—"}</code></td></tr>
          <tr><td>Role claim</td><td><code>${auth.oidc_role_claim || "chorus_roles"}</code></td></tr>
        </tbody></table>
         <p class="score-meta" style="margin-top:0.75rem">Bearer formats: admin token, token|user|role, or OIDC JWT when enabled.</p>`,
        "Access modes",
        80
      )}
      ${section(
        "Recommendations",
        `<p class="score-meta" style="margin:0 0 0.75rem">${
          payload.recommendations?.predictive ? "Predictive from retained metrics" : "Baseline"
        } · ${payload.recommendations?.samples ?? 0} samples</p>
         <table class="data"><thead><tr><th>Title</th><th>Severity</th></tr></thead><tbody>${
           recs
             .slice(0, 8)
             .map(
               (r) =>
                 `<tr><td>${r.title || r.id || "—"}</td><td>${r.severity || r.level || "info"}</td></tr>`
             )
             .join("") || `<tr><td colspan="2" class="empty">Collecting metric samples…</td></tr>`
         }</tbody></table>`,
        "Ops intelligence",
        90
      )}
    </div>
    <div class="grid-2">
      ${section(
        "Stack licenses",
        `<table class="data"><thead><tr><th>Product</th><th>Status</th><th>Tier / exp</th></tr></thead><tbody>${
          Object.entries(payload.stack?.products || {})
            .map(
              ([name, p]) =>
                `<tr><td>${name}</td><td>${p.status || "—"}</td><td>${p.tier || "—"} ${
                  p.exp ? "· " + p.exp : ""
                }</td></tr>`
            )
            .join("") || `<tr><td colspan="3" class="empty">No stack keys configured</td></tr>`
        }</tbody></table>
         <p class="score-meta" style="margin-top:0.75rem">Env keys only — never phone-home.</p>`,
        "Sibling keys",
        110
      )}
      ${section(
        "Asset Graph",
        `<p class="score-meta" style="margin:0 0 0.75rem">${assets.length} assets · ${
          (payload.graph?.edges || []).length
        } edges</p>
         <table class="data"><thead><tr><th>Kind</th><th>Name</th></tr></thead><tbody>${
           assets
             .slice(0, 12)
             .map((a) => `<tr><td>${a.kind}</td><td>${a.name}</td></tr>`)
             .join("") || `<tr><td colspan="2" class="empty">Sync after fleet join</td></tr>`
         }</tbody></table>`,
        "Blast radius ready",
        100
      )}
    </div>
    <div class="grid-2">
      ${section(
        "Join token",
        `<p class="score-meta">Issue a token for worker enrollment. Agents read <code>CHORUSCONTROL_JOIN_TOKEN</code>.</p>
         <pre id="tokenOut" style="margin:0.85rem 0 0;padding:0.85rem;background:var(--paper-2);border-radius:var(--radius);font-size:0.78rem;word-break:break-all">No token yet — click Create join token</pre>`,
        "Fleet enroll",
        140
      )}
      ${section(
        "Tenants",
        `<table class="data"><thead><tr><th>ID</th><th>Name</th></tr></thead><tbody>${
          (payload.tenants?.tenants || [])
            .map((t) => `<tr><td>${t.tenant_id}</td><td>${t.name || "—"}</td></tr>`)
            .join("") || `<tr><td colspan="2" class="empty">default</td></tr>`
        }</tbody></table>`,
        "max_tenants enforced",
        150
      )}
    </div>
    <div class="grid-2">
      ${section(
        "Incidents",
        `<table class="data"><thead><tr><th>Title</th><th>State</th><th>Assets</th></tr></thead><tbody>${
          incidents
            .slice(0, 10)
            .map(
              (i) =>
                `<tr><td>${escapeHtml(i.title || "")}</td><td>${escapeHtml(
                  i.state
                )}</td><td>${(i.assets || []).length}</td></tr>`
            )
            .join("") || `<tr><td colspan="3" class="empty">None</td></tr>`
        }</tbody></table>`,
        "Intelligence API",
        160
      )}
      ${section(
        "Compliance findings",
        `<table class="data"><thead><tr><th>Sev</th><th>Code</th><th>Title</th></tr></thead><tbody>${
          findings
            .slice(0, 10)
            .map(
              (f) =>
                `<tr><td>${escapeHtml(f.severity)}</td><td><code>${escapeHtml(
                  f.code
                )}</code></td><td>${escapeHtml(f.title)}</td></tr>`
            )
            .join("") || `<tr><td colspan="3" class="empty">Run Compliance scan</td></tr>`
        }</tbody></table>
         <p class="score-meta" style="margin-top:0.5rem">Automated posture — not a SOC2 attestation. Enterprise policies: ${
           ep.length
         }</p>`,
        "Trust packaging",
        170
      )}
    </div>
  `;

  document.getElementById("mkToken").onclick = async () => {
    const r = await j("/api/v1/fleet/join-tokens", {
      method: "POST",
      body: JSON.stringify({ max_uses: 10 }),
    });
    document.getElementById("tokenOut").textContent = r.join_token;
  };
  const cmpScan = document.getElementById("cmpScan");
  if (cmpScan) {
    cmpScan.onclick = async () => {
      const r = await j("/api/v1/compliance/scan", { method: "POST", body: "{}" });
      out.textContent = JSON.stringify(r, null, 2);
      load();
    };
  }
  document.getElementById("soc2").onclick = async () => {
    const r = await fetch("/api/v1/admin/soc2-export", { headers });
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "choruscontrol-soc2.zip";
    a.click();
  };
  const installBtn = document.getElementById("installLic");
  if (installBtn) {
    installBtn.onclick = async () => {
      const key = document.getElementById("licKey").value.trim();
      if (!key) return;
      const r = await j("/api/v1/admin/license", {
        method: "POST",
        body: JSON.stringify({ license_key: key }),
      });
      appendChat("bot", `License installed: ${r.state}`);
      load();
    };
  }
  const onlineBtn = document.getElementById("onlineLic");
  if (onlineBtn) {
    onlineBtn.onclick = async () => {
      const r = await j("/api/v1/admin/license/online-check", { method: "POST", body: "{}" });
      out.textContent = JSON.stringify(r, null, 2);
      appendChat(
        "bot",
        `Side 1 online check: ${r.check?.result?.status || r.check?.reason || r.check?.error || r.license?.state}`
      );
      load();
    };
  }
}

async function soft(url, fallback = null) {
  try {
    return await j(url);
  } catch (e) {
    console.warn("soft fetch failed", url, e);
    return fallback;
  }
}

async function load() {
  view.innerHTML = skeleton();
  try {
    const okAuth = await resolveToken();
    if (!okAuth && !token) {
      view.innerHTML = section(
        "Sign in",
        `<p class="err">API token required.</p>
         <p class="score-meta">Healthcare demo token: <code>healthcare-demo-token</code> — paste in the left rail and click Apply.</p>`
      );
      return;
    }
    const lic = await j("/api/v1/admin/license");
    const licEl = document.getElementById("lic");
    const chip = document.getElementById("licChip");
    if (licEl) licEl.textContent = lic.state;
    if (chip) chip.dataset.state = lic.state || "";
    if (lic.portal_url) document.getElementById("renewLink").href = lic.portal_url;

    let payload = {};
    if (tab === "overview") {
      let recent = await soft("/api/v1/traces/recent?tenant_id=aurora-health", { traces: [] });
      if (!(recent.traces || []).length) {
        recent = await soft("/api/v1/traces/recent?tenant_id=default", { traces: [] });
      }
      if (!(recent.traces || []).length) {
        try {
          await j("/api/v1/traces/seed", {
            method: "POST",
            body: JSON.stringify({ tenant_id: "aurora-health" }),
          });
        } catch (_) {
          try {
            await j("/api/v1/traces/seed", {
              method: "POST",
              body: JSON.stringify({ tenant_id: "default" }),
            });
          } catch (__) {}
        }
      }
      const [matrix, caps, fleet, drift, score, tax, driver, dogfood, pipelines, incidents, findings, versionDiff] =
        await Promise.all([
          soft("/api/v1/health/matrix", {}),
          soft("/api/v1/health/caps", {}),
          soft("/api/v1/fleet/topology", { nodes: [] }),
          soft("/api/v1/policy/drift", { drifts: [] }),
          soft("/api/v1/metrics/ai-score", { overall: 0, dimensions: {}, demo: true }),
          soft("/api/v1/metrics/token-tax", { demo: true }),
          soft("/api/v1/metrics/prismdriver", {}),
          soft("/api/v1/status/dogfood", {}),
          soft("/api/v1/pipelines/live", {
            execution: { stages: [] },
            fleet: [],
            graph: { nodes: [], edges: [] },
            cascade: null,
          }),
          soft("/api/v1/incidents", { incidents: [] }),
          soft("/api/v1/compliance/findings", { findings: [] }),
          soft("/api/v1/fleet/version-diff?tenant_id=default", {}),
        ]);
      payload = {
        matrix,
        caps,
        fleet,
        drift,
        score,
        tax,
        driver,
        dogfood,
        pipelines,
        incidents,
        findings,
        versionDiff,
      };
      if (payload.caps?.guard?.demo || payload.tax?.demo || payload.score?.demo) {
        document.getElementById("demoBanner").hidden = false;
      }
      lastRender = () => renderOverview(payload);
      await renderOverview(payload);
    } else if (tab === "trace") {
      const [recentT, pipelines] = await Promise.all([
        soft("/api/v1/traces/recent", { traces: [], entries: [] }),
        soft("/api/v1/pipelines/live", { execution: { stages: [] } }),
      ]);
      payload = recentT;
      payload.pipelines = pipelines;
      lastRender = () => renderTrace(payload);
      await renderTrace(payload);
    } else if (tab === "taxonomy") {
      const authMeta = await soft("/api/v1/admin/auth", {});
      if (authMeta && authMeta.demo_mode === false && authMeta.taxonomy_ready === false) {
        const hint =
          authMeta.taxonomy_packs?.install_hint ||
          'pip install "choruscontrol[server,prism]"';
        const msgs = (authMeta.taxonomy_packs?.messages || []).join(" · ") || "PrismRAG + PrismGuard required";
        actions.innerHTML = "";
        view.innerHTML = section(
          "Taxonomy unavailable",
          `<p style="margin:0 0 0.75rem">${msgs}</p>
           <p class="score-meta">When <code>DEMO_MODE=0</code>, Taxonomy does not fall back to NullRAG DEMO.</p>
           <p style="margin-top:1rem">Install: <code>${hint}</code></p>`,
          "Requires choruscontrol[prism]"
        );
        lastRender = null;
        return;
      }
      let taxTenant = "default";
      try {
        const tenants = await soft("/api/v1/admin/tenants", { tenants: [] });
        const ids = (tenants.tenants || []).map((t) => t.tenant_id || t.id).filter(Boolean);
        if (ids.includes("aurora-health")) taxTenant = "aurora-health";
        else if (ids[0]) taxTenant = ids[0];
      } catch (_) {}
      const q = `tenant_id=${encodeURIComponent(taxTenant)}`;
      const [tree, partitions, health] = await Promise.all([
        soft(`/api/v1/taxonomy/tree?${q}`, { categories: [] }),
        soft(`/api/v1/taxonomy/partitions?${q}`, { partitions: [] }),
        soft(`/api/v1/taxonomy/chunks/health?${q}`, { decay: [] }),
      ]);
      payload = { tree, partitions, health, tenantId: taxTenant };
      lastRender = () => renderTaxonomy(payload);
      await renderTaxonomy(payload);
    } else if (tab === "cortex" || tab === "memory") {
      let cxTenant = "default";
      try {
        const tenants = await soft("/api/v1/admin/tenants", { tenants: [] });
        const ids = (tenants.tenants || []).map((t) => t.tenant_id || t.id).filter(Boolean);
        if (ids.includes("aurora-health")) cxTenant = "aurora-health";
        else if (ids[0]) cxTenant = ids[0];
      } catch (_) {}
      const snapshot = await soft(
        `/api/v1/cortex/snapshot?tenant_id=${encodeURIComponent(cxTenant)}`,
        { activity: [], chunks: [], facts: [], conflicts: [], engine: "null", demo: true }
      );
      payload = { snapshot, tenantId: cxTenant };
      lastRender = () => renderCortex(payload);
      await renderCortex(payload);
    } else if (tab === "guard") {
      const [policy, logs] = await Promise.all([
        soft("/api/v1/guard/policy", { policy: {} }),
        soft("/api/v1/guard/logs", { logs: [] }),
      ]);
      payload = { policy, logs };
      lastRender = () => renderGuard(payload);
      await renderGuard(payload);
    } else if (tab === "admin") {
      const [doctor, graph, auth, recommendations, stack, tenants, incidents, findings, enterprise] =
        await Promise.all([
          soft("/api/v1/admin/doctor", {}),
          soft("/api/v1/graph", { assets: [], edges: [] }),
          soft("/api/v1/admin/auth", { local_token: true, oidc_enabled: false }),
          soft("/api/v1/recommendations", { recommendations: [], predictive: false, samples: 0 }),
          soft("/api/v1/admin/stack-licenses", { products: {} }),
          soft("/api/v1/admin/tenants", { tenants: [] }),
          soft("/api/v1/incidents", { incidents: [] }),
          soft("/api/v1/compliance/findings", { findings: [] }),
          soft("/api/v1/enterprise/policies", { policies: [] }),
        ]);
      payload = {
        license: lic,
        doctor,
        graph,
        auth,
        recommendations,
        stack,
        tenants,
        incidents,
        findings,
        enterprise,
      };
      lastRender = () => renderAdmin(payload);
      await renderAdmin(payload);
    }
    out.textContent = JSON.stringify(payload, null, 2);

    // First visit: open Ops Assistant so it is discoverable
    if (!localStorage.getItem("cc_chat_seen")) {
      localStorage.setItem("cc_chat_seen", "1");
      setChatOpen(true);
      appendChat(
        "bot",
        "Welcome — Ops Assistant runs Guard → ChorusGraph → Shine on your question, then answers from live Overview telemetry (no world-truth). Pick Light or Dark in the rail. Try “Explain scores” or “What does the clinical agent do?”."
      );
    }
  } catch (e) {
    view.innerHTML = section(
      "Unable to load",
      `<p class="err">${String(e)}</p><pre style="font-size:0.75rem">${JSON.stringify(e.data || {}, null, 2)}</pre>
       <p class="score-meta">If this persists, restart mother: <code>python -m choruscontrol.cli serve</code></p>`
    );
    out.textContent = String(e);
  }
}

load();
