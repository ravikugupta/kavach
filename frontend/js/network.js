// ── D3 Force-Directed Network Graph ──────────────────────────────────────────
const NODE_COLORS = {
  accused:  "#4c8dff",
  victim:   "#ef4444",
  location: "#10b981",
};

const NODE_RADIUS = { accused: 20, victim: 14, location: 12 };

let simulation = null;   // D3 simulation — keep reference to stop/restart

async function loadNetwork() {
  const accusedId = document.getElementById("accused-id-input").value;
  if (!accusedId) return;

  try {
    const [network, groups] = await Promise.all([
      apiGet(`/api/analytics/accused/${accusedId}/network?depth=1`),
      apiGet("/api/analytics/organized-groups?min_group_size=3"),
    ]);
    renderNetworkGraph(network);
    renderGroups(groups);
  } catch (err) {
    console.error("Network load failed:", err);
    const svg = document.getElementById("network-svg");
    if (svg) svg.innerHTML =
      `<text x="20" y="40" fill="var(--danger)">Could not load network. Check accused ID and backend.</text>`;
  }
}

function renderNetworkGraph(network) {
  const container = document.getElementById("network-svg");
  if (!container) return;

  // Stop any running simulation
  if (simulation) simulation.stop();

  // Clear previous render
  container.innerHTML = "";

  const width  = container.clientWidth  || 800;
  const height = parseInt(container.getAttribute("height")) || 480;

  // Build D3 nodes + links from API response
  const nodeMap = {};
  network.nodes.forEach(n => { nodeMap[`${n.type}:${n.id}`] = n; });

  const nodes = network.nodes.map(n => ({
    id:    `${n.type}:${n.id}`,
    label: n.label,
    type:  n.type,
    raw:   n,
  }));

  const links = network.edges.map(e => ({
    source:   e.source,
    target:   e.target,
    relation: e.relation,
  }));

  // Create SVG via D3
  const svg = d3.select(container)
    .attr("width", width)
    .attr("height", height);

  // Defs: arrowhead marker
  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 28)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "rgba(100,130,220,0.4)");

  // Link group
  const linkGroup = svg.append("g").attr("class", "links");
  const linkSel = linkGroup.selectAll("line")
    .data(links).enter().append("line")
    .attr("stroke", "rgba(100,130,220,0.3)")
    .attr("stroke-width", 1.5)
    .attr("marker-end", "url(#arrow)");

  // Link labels
  const linkLabelSel = linkGroup.selectAll("text")
    .data(links).enter().append("text")
    .attr("font-size", 9)
    .attr("fill", "var(--text-dim)")
    .attr("text-anchor", "middle")
    .text(d => d.relation.replace(/_/g, " "));

  // Node group
  const nodeGroup = svg.append("g").attr("class", "nodes");
  const nodeSel = nodeGroup.selectAll("g")
    .data(nodes).enter().append("g")
    .attr("class", "node")
    .style("cursor", "pointer")
    .call(
      d3.drag()
        .on("start", dragStart)
        .on("drag",  dragging)
        .on("end",   dragEnd)
    );

  nodeSel.append("circle")
    .attr("r", d => NODE_RADIUS[d.type] || 14)
    .attr("fill", d => NODE_COLORS[d.type] || "#888")
    .attr("stroke", "rgba(255,255,255,0.15)")
    .attr("stroke-width", 2);

  // Root node gets a glow ring
  nodeSel.filter((_, i) => i === 0).append("circle")
    .attr("r", 26)
    .attr("fill", "none")
    .attr("stroke", "#4c8dff")
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", "4 3")
    .attr("opacity", 0.5);

  nodeSel.append("text")
    .attr("dy", d => (NODE_RADIUS[d.type] || 14) + 13)
    .attr("text-anchor", "middle")
    .attr("font-size", 11)
    .attr("fill", "var(--text-muted)")
    .text(d => d.label.length > 18 ? d.label.slice(0, 16) + "…" : d.label);

  // Tooltip
  const tooltip = d3.select("body").select(".node-tooltip");
  const tip = tooltip.size()
    ? tooltip
    : d3.select("body").append("div").attr("class", "node-tooltip");

  nodeSel
    .on("mouseover", (event, d) => {
      tip.classed("visible", true)
        .html(`<strong>${d.label}</strong><br/>Type: ${d.type}<br/>ID: ${d.raw.id}`)
        .style("left", (event.clientX + 12) + "px")
        .style("top",  (event.clientY - 8)  + "px");
    })
    .on("mousemove", event => {
      tip.style("left", (event.clientX + 12) + "px")
         .style("top",  (event.clientY - 8)  + "px");
    })
    .on("mouseout", () => tip.classed("visible", false));

  // D3 force simulation
  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(110))
    .force("charge", d3.forceManyBody().strength(-320))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(d => (NODE_RADIUS[d.type] || 14) + 20))
    .on("tick", ticked);

  function ticked() {
    linkSel
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    linkLabelSel
      .attr("x", d => (d.source.x + d.target.x) / 2)
      .attr("y", d => (d.source.y + d.target.y) / 2);

    nodeSel.attr("transform", d =>
      `translate(${Math.max(30, Math.min(width  - 30, d.x))},`
      +           `${Math.max(30, Math.min(height - 30, d.y))})`);
  }

  function dragStart(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }

  function dragging(event, d) {
    d.fx = event.x; d.fy = event.y;
  }

  function dragEnd(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  }
}

// ── Organized Groups list ─────────────────────────────────────────────────────
function renderGroups(data) {
  const el = document.getElementById("groups-list");
  if (!el) return;
  el.innerHTML = "";
  if (!data.groups.length) {
    el.innerHTML = `<div class="list-item">No organized groups detected with the current threshold.</div>`;
    return;
  }
  data.groups.forEach((g, idx) => {
    const names = g.members.map(m => `${m.name} (#${m.accused_id})`).join(", ");
    const cls = g.avg_risk_score >= 0.7 ? "high" : (g.avg_risk_score >= 0.4 ? "med" : "low");
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <span class="rank">${idx + 1}</span>
      <span class="name">Group of ${g.group_size}: ${names}</span>
      <span class="risk-badge ${cls}">avg ${g.avg_risk_score}</span>`;
    el.appendChild(item);
  });
}
