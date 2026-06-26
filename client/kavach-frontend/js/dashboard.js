// ── Chart.js instances (kept so we can destroy/re-create on refresh) ─────────
let crimeTypeChart = null;
let monthlyTrendChart = null;
let socioChart = null;

// ── Colour helpers ────────────────────────────────────────────────────────────
const CHART_COLORS = [
  "#4c8dff","#22d3ee","#f59e0b","#10b981","#ef4444",
  "#a78bfa","#fb923c","#34d399","#f472b6","#60a5fa",
];

function chartTextColor() {
  return getComputedStyle(document.documentElement)
    .getPropertyValue("--text-muted").trim() || "#7889aa";
}

function chartGridColor() {
  return getComputedStyle(document.documentElement)
    .getPropertyValue("--border").trim() || "rgba(100,130,220,0.12)";
}

function baseChartOptions(yLabel = "") {
  const textColor = chartTextColor();
  const gridColor = chartGridColor();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: textColor, font: { size: 11 } } },
    },
    scales: {
      x: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor } },
      y: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor },
           title: { display: !!yLabel, text: yLabel, color: textColor } },
    },
  };
}

// ── Main dashboard loader ─────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [summary, hotspots, trends, socio, repeat, forecast] = await Promise.all([
      apiGet("/api/analytics/summary"),
      apiGet("/api/analytics/hotspots?top_n=6"),
      apiGet("/api/analytics/trends"),
      apiGet("/api/analytics/sociological"),
      apiGet("/api/analytics/repeat-offenders?min_priors=2&top_n=8"),
      apiGet("/api/forecast/trends"),
    ]);

    renderStatCards(summary);
    renderHotspots(hotspots);
    renderCrimeTypeChart(trends.by_crime_type);
    renderMonthlyTrendChart(trends.by_month);
    renderSocioChart(socio.accused_economic_background);
    renderRepeatOffenders(repeat);
    renderForecast(forecast);
  } catch (err) {
    console.error("Dashboard load failed:", err);
  }
}

// ── Stat cards ────────────────────────────────────────────────────────────────
function renderStatCards(s) {
  const map = {
    "stat-total-firs":        { value: s.total_firs,            sub: `${s.open_firs} open`,             cls: "" },
    "stat-accused":           { value: s.total_accused,         sub: `${s.high_risk_accused} high-risk`, cls: "danger" },
    "stat-victims":           { value: s.total_victims,         sub: "total victims",                   cls: "warning" },
    "stat-alerts":            { value: s.active_alerts,         sub: "active alerts",                   cls: "cyan" },
  };
  for (const [id, cfg] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.querySelector(".stat-value").textContent = cfg.value ?? "–";
    const sub = el.querySelector(".stat-sub");
    if (sub) sub.textContent = cfg.sub;
  }
}

// ── Hotspots list ─────────────────────────────────────────────────────────────
function renderHotspots(data) {
  const el = document.getElementById("hotspots-list");
  if (!el) return;
  el.innerHTML = "";
  data.hotspots.forEach((h, i) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <span class="rank">${i + 1}</span>
      <span class="name">${h.area_name}, ${h.city}</span>
      <span class="risk-badge high">${h.case_count} cases</span>`;
    el.appendChild(item);
  });
}

// ── Crime Type Bar Chart (Chart.js) ──────────────────────────────────────────
function renderCrimeTypeChart(dataObj) {
  const ctx = document.getElementById("crime-type-chart");
  if (!ctx) return;
  const entries = Object.entries(dataObj || {}).slice(0, 10);
  const labels = entries.map(([k]) => k);
  const values = entries.map(([, v]) => v);

  if (crimeTypeChart) crimeTypeChart.destroy();
  crimeTypeChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Cases",
        data: values,
        backgroundColor: CHART_COLORS.slice(0, labels.length),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      ...baseChartOptions("Cases"),
      indexAxis: "y",
      plugins: { legend: { display: false } },
    },
  });
}

// ── Monthly Trend Line Chart (Chart.js) ──────────────────────────────────────
function renderMonthlyTrendChart(byMonth) {
  const ctx = document.getElementById("monthly-trend-chart");
  if (!ctx) return;
  const labels = Object.keys(byMonth || {});
  const values = Object.values(byMonth || {});

  if (monthlyTrendChart) monthlyTrendChart.destroy();
  monthlyTrendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Total FIRs",
        data: values,
        borderColor: "#4c8dff",
        backgroundColor: "rgba(76,141,255,0.1)",
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: "#4c8dff",
      }],
    },
    options: baseChartOptions("FIRs"),
  });
}

// ── Socio-Economic Doughnut Chart (Chart.js) ─────────────────────────────────
function renderSocioChart(dataObj) {
  const ctx = document.getElementById("socio-chart");
  if (!ctx) return;
  const entries = Object.entries(dataObj || {});
  const labels = entries.map(([k]) => k);
  const values = entries.map(([, v]) => v);

  if (socioChart) socioChart.destroy();
  socioChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: CHART_COLORS.slice(0, labels.length),
        borderColor: "rgba(0,0,0,0.2)",
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: chartTextColor(), font: { size: 11 }, boxWidth: 12 },
        },
      },
    },
  });
}

// ── Repeat Offenders list ─────────────────────────────────────────────────────
function renderRepeatOffenders(data) {
  const el = document.getElementById("repeat-offenders-list");
  if (!el) return;
  el.innerHTML = "";
  data.repeat_offenders.forEach((r, i) => {
    const cls = r.risk_score >= 0.7 ? "high" : (r.risk_score >= 0.4 ? "med" : "low");
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <span class="rank">${i + 1}</span>
      <span class="name">#${r.accused_id} ${r.name}</span>
      <span class="detail">${r.prior_offenses} priors</span>
      <span class="risk-badge ${cls}">${r.risk_score}</span>`;
    el.appendChild(item);
  });
}

// ── Forecast Chips ────────────────────────────────────────────────────────────
function renderForecast(data) {
  const el = document.getElementById("forecast-list");
  if (!el) return;
  el.innerHTML = "";

  if (!data || !data.forecasts || !data.forecasts.length) {
    el.innerHTML = `<p style="color:var(--text-muted);font-size:13px;">No forecast data available.</p>`;
    return;
  }

  // Show top 6 by absolute slope
  const top = data.forecasts.slice(0, 6);
  const row = document.createElement("div");
  row.className = "forecast-row";

  top.forEach(f => {
    const trendCls = f.trend === "rising" ? "up" : (f.trend === "declining" ? "down" : "flat");
    const trendIcon = f.trend === "rising" ? "▲" : (f.trend === "declining" ? "▼" : "→");
    const chip = document.createElement("div");
    chip.className = `forecast-chip ${trendCls}`;
    chip.innerHTML = `
      <span class="fc-label">${f.crime_type}</span>
      <span class="fc-value">${f.predicted_next_month}</span>
      <span class="fc-trend ${trendCls}">${trendIcon} ${f.trend} (slope ${f.trend_slope})</span>`;
    row.appendChild(chip);
  });
  el.appendChild(row);

  const note = document.createElement("p");
  note.style.cssText = "font-size:11px;color:var(--text-dim);margin-top:8px;";
  note.textContent = data.evidence;
  el.appendChild(note);
}

// ── Alerts loader (also used by alerts view) ──────────────────────────────────
async function loadAlerts() {
  const el = document.getElementById("alerts-list");
  if (!el) return;
  el.innerHTML = `<div class="skeleton skeleton-text" style="height:60px;margin-bottom:8px;"></div>`.repeat(3);
  try {
    const data = await apiGet("/api/analytics/early-warning");
    el.innerHTML = "";
    if (!data.alerts.length) {
      el.innerHTML = `<div class="list-item">No active alerts in the current dataset.</div>`;
      return;
    }
    data.alerts.forEach(a => {
      const item = document.createElement("div");
      item.className = `alert-item ${a.type}`;
      const sev = a.severity || "low";
      item.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <span class="alert-pulse"></span>
          <span class="alert-type ${a.type}">${a.type.replace(/_/g, " ")}</span>
          <span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;
                       padding:2px 6px;border-radius:4px;margin-left:4px;
                       background:${sev === "high" ? "var(--danger-dim)" : sev === "medium" ? "var(--warning-dim)" : "rgba(255,255,255,0.05)"};
                       color:${sev === "high" ? "var(--danger)" : sev === "medium" ? "var(--warning)" : "var(--text-muted)"};">
            ${sev}
          </span>
        </div>
        <div>${a.message}</div>`;
      el.appendChild(item);
    });
    const note = document.createElement("p");
    note.style.cssText = "font-size:11px;color:var(--text-dim);margin-top:12px;";
    note.textContent = data.evidence;
    el.appendChild(note);
  } catch (err) {
    el.innerHTML = `<div class="list-item">Failed to load alerts. Is the backend running?</div>`;
  }
}
