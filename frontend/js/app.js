// ── Navigation ─────────────────────────────────────────────
const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");

navItems.forEach(item => {
  item.addEventListener("click", () => {
    navItems.forEach(i => i.classList.remove("active"));
    views.forEach(v => v.classList.remove("active"));

    item.classList.add("active");
    const target = document.getElementById(`view-${item.dataset.view}`);
    if (target) target.classList.add("active");

    if (item.dataset.view === "dashboard") loadDashboard();
    if (item.dataset.view === "network") loadNetwork();
    if (item.dataset.view === "alerts") loadAlerts();
  });
});

// ── Dark / Light Mode Toggle ────────────────────────────────
const themeToggleBtn = document.getElementById("theme-toggle");
const savedTheme = localStorage.getItem("kavach-theme") || "dark";

function applyTheme(theme) {
  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
    if (themeToggleBtn) themeToggleBtn.textContent = "☀️";
  } else {
    document.documentElement.removeAttribute("data-theme");
    if (themeToggleBtn) themeToggleBtn.textContent = "🌙";
  }
  localStorage.setItem("kavach-theme", theme);
}

applyTheme(savedTheme);

if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "light" ? "dark" : "light");
  });
}
