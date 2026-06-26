// Base URL of the FastAPI backend (Catalyst Advanced I/O Function).
// When deployed on Catalyst, the Advanced I/O function is served at:
//   /server/<function-name>  (same origin via Catalyst routing)
// Locally (dev server): leave as "" to use relative paths.
const API_BASE = (function () {
  // Detect Catalyst environment by checking hostname
  const host = window.location.hostname;
  if (host.includes("catalyst.zohocloud.in") || host.includes("catalyst.zoho.in")) {
    return "/server/kavach-api";
  }
  // Local development: FastAPI serves both API and static files
  return "";
})();

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}
