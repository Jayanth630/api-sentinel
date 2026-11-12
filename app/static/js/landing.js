/**
 * API SENTINEL - WELCOME / LANDING PAGE CONTROLLER
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Theme Management (synchronized with Dashboard)
  const savedTheme = localStorage.getItem("apisentinel_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcons(savedTheme);

  const themeToggle = document.getElementById("landingThemeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const nextTheme = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", nextTheme);
      localStorage.setItem("apisentinel_theme", nextTheme);
      updateThemeIcons(nextTheme);
    });
  }

  function updateThemeIcons(theme) {
    const moon = document.querySelector(".theme-moon-icon");
    const sun = document.querySelector(".theme-sun-icon");
    if (moon && sun) {
      if (theme === "dark") {
        moon.style.display = "block";
        sun.style.display = "none";
      } else {
        moon.style.display = "none";
        sun.style.display = "block";
      }
    }
  }

  // 2. Fetch Real Telemetry to Populate Hero Preview
  fetchHeroTelemetry();

  async function fetchHeroTelemetry() {
    try {
      const res = await fetch("/api/dashboard/stats");
      if (!res.ok) return;
      const json = await res.json();
      if (!json.success || !json.data) return;

      const d = json.data;
      const kpiUptime = document.getElementById("heroKpiUptime");
      const kpiAvg = document.getElementById("heroKpiAvg");
      const kpiTotal = document.getElementById("heroKpiTotal");
      const kpiIncidents = document.getElementById("heroKpiIncidents");

      if (kpiUptime) kpiUptime.textContent = `${(d.system_uptime !== undefined ? d.system_uptime : 100).toFixed(1)}%`;
      if (kpiAvg) kpiAvg.textContent = `${d.system_avg_latency || 0} ms`;
      if (kpiTotal) kpiTotal.textContent = d.total_endpoints ?? 6;
      if (kpiIncidents) kpiIncidents.textContent = d.active_incidents_count ?? 0;
    } catch (e) {
      // Graceful fallback to static numbers if server is quiet
    }
  }

  // 3. Smooth scrolling for internal anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function(e) {
      const targetId = this.getAttribute("href");
      if (targetId && targetId !== "#") {
        const targetEl = document.querySelector(targetId);
        if (targetEl) {
          e.preventDefault();
          targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  });
});
