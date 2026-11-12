/**
 * API SENTINEL - CORE APPLICATION MANAGER
 */

const App = {
  currentView: "dashboard",
  theme: localStorage.getItem("apisentinel_theme") || "dark",
  refreshTimer: null,
  refreshIntervalMs: 10000,

  init() {
    this.initTheme();
    this.initNavigation();
    this.initAutoRefresh();
    this.initGlobalEvents();
    this.initDemoSeeder();

    // Initial load
    this.loadCurrentView();
  },

  /* -------------------------------------------------------------
     THEME MANAGEMENT
     ------------------------------------------------------------- */
  initTheme() {
    document.documentElement.setAttribute("data-theme", this.theme);
    this.updateThemeIcons();

    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        this.theme = this.theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", this.theme);
        localStorage.setItem("apisentinel_theme", this.theme);
        this.updateThemeIcons();

        // Notify charts to update theme colors
        if (window.Dashboard && Dashboard.updateChartThemes) {
          Dashboard.updateChartThemes();
        }
        if (window.Analytics && Analytics.updateChartThemes) {
          Analytics.updateChartThemes();
        }
      });
    }
  },

  updateThemeIcons() {
    const moonIcon = document.querySelector(".theme-moon-icon");
    const sunIcon = document.querySelector(".theme-sun-icon");
    if (moonIcon && sunIcon) {
      if (this.theme === "dark") {
        moonIcon.style.display = "block";
        sunIcon.style.display = "none";
      } else {
        moonIcon.style.display = "none";
        sunIcon.style.display = "block";
      }
    }
  },

  /* -------------------------------------------------------------
     NAVIGATION & VIEW SWITCHING
     ------------------------------------------------------------- */
  initNavigation() {
    const navLinks = document.querySelectorAll(".sidebar-nav .nav-link");
    navLinks.forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const targetView = link.getAttribute("data-view");
        if (targetView) {
          this.switchView(targetView);
        }
      });
    });

    // Mobile sidebar toggle
    const menuToggle = document.getElementById("menuToggleBtn");
    const sidebar = document.getElementById("appSidebar");
    if (menuToggle && sidebar) {
      menuToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });

      // Close sidebar when clicking outside on mobile
      document.addEventListener("click", (e) => {
        if (window.innerWidth <= 768 && sidebar.classList.contains("open")) {
          if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove("open");
          }
        }
      });
    }
  },

  switchView(viewName) {
    this.currentView = viewName;

    // Update active nav link
    document.querySelectorAll(".sidebar-nav .nav-link").forEach(link => {
      if (link.getAttribute("data-view") === viewName) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Update active view section
    document.querySelectorAll(".view-section").forEach(sec => {
      sec.classList.remove("active");
    });
    const targetSection = document.getElementById(`view${viewName.charAt(0).toUpperCase() + viewName.slice(1)}`);
    if (targetSection) {
      targetSection.classList.add("active");
    }

    // Update page title
    const titles = {
      dashboard: "Dashboard Overview",
      endpoints: "Monitored Endpoints",
      analytics: "Health & Latency Analytics",
      incidents: "Downtime Incidents",
      settings: "Settings & API Documentation"
    };
    const titleEl = document.getElementById("pageTitle");
    if (titleEl) {
      titleEl.textContent = titles[viewName] || "API Sentinel";
    }

    // Close mobile menu if open
    const sidebar = document.getElementById("appSidebar");
    if (sidebar && window.innerWidth <= 768) {
      sidebar.classList.remove("open");
    }

    // Trigger view-specific data refresh
    this.loadCurrentView();
  },

  loadCurrentView() {
    switch (this.currentView) {
      case "dashboard":
        if (window.Dashboard) Dashboard.loadData();
        break;
      case "endpoints":
        if (window.Endpoints) Endpoints.loadData();
        break;
      case "analytics":
        if (window.Analytics) Analytics.loadData();
        break;
      case "incidents":
        if (window.Incidents) Incidents.loadData();
        break;
      case "settings":
        break;
    }
    // Update badge count across sidebar
    this.updateSidebarCounters();
  },

  /* -------------------------------------------------------------
     AUTO-REFRESH SCHEDULER
     ------------------------------------------------------------- */
  initAutoRefresh() {
    const select = document.getElementById("refreshIntervalSelect");
    if (select) {
      select.addEventListener("change", (e) => {
        this.refreshIntervalMs = parseInt(e.target.value, 10);
        this.resetAutoRefresh();
      });
    }
    this.resetAutoRefresh();
  },

  resetAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
    if (this.refreshIntervalMs > 0) {
      this.refreshTimer = setInterval(() => {
        this.loadCurrentView();
      }, this.refreshIntervalMs);
    }
  },

  /* -------------------------------------------------------------
     GLOBAL ACTIONS & SEEDER
     ------------------------------------------------------------- */
  initGlobalEvents() {
    // Open Add Modal from topbar
    const topAddBtn = document.getElementById("btnOpenAddModal");
    if (topAddBtn) {
      topAddBtn.addEventListener("click", () => {
        if (window.Endpoints) Endpoints.openModal();
      });
    }

    // Export endpoints CSV from Endpoints view
    const exportEpBtn = document.getElementById("btnExportEndpointsCsv");
    if (exportEpBtn) {
      exportEpBtn.addEventListener("click", () => {
        window.location.href = "/api/export/endpoints/csv";
      });
    }

    // Export analytics CSV
    const exportAnaBtn = document.getElementById("btnExportAnalyticsCsv");
    if (exportAnaBtn) {
      exportAnaBtn.addEventListener("click", () => {
        const sel = document.getElementById("analyticsEndpointSelect");
        const epId = sel ? sel.value : "";
        window.location.href = epId ? `/api/export/checks/csv?endpoint_id=${epId}` : "/api/export/checks/csv";
      });
    }

    // Export incidents CSV
    const exportIncBtn = document.getElementById("btnExportIncidentsCsv");
    if (exportIncBtn) {
      exportIncBtn.addEventListener("click", () => {
        window.location.href = "/api/export/checks/csv";
      });
    }

    // Brand header click -> Dashboard
    const brandHeader = document.querySelector(".sidebar-header");
    if (brandHeader) {
      brandHeader.style.cursor = "pointer";
      brandHeader.title = "Return to Dashboard";
      brandHeader.addEventListener("click", () => this.switchView("dashboard"));
    }

    // Dashboard KPI cards click-through navigation
    const totalCard = document.getElementById("kpiTotalApis")?.closest(".stat-card");
    if (totalCard) {
      totalCard.style.cursor = "pointer";
      totalCard.title = "View all monitored APIs";
      totalCard.addEventListener("click", () => this.switchView("endpoints"));
    }

    const healthyCard = document.getElementById("kpiHealthyApis")?.closest(".stat-card");
    if (healthyCard) {
      healthyCard.style.cursor = "pointer";
      healthyCard.title = "Filter healthy APIs";
      healthyCard.addEventListener("click", () => {
        this.switchView("endpoints");
        const sel = document.getElementById("filterStatusSelect");
        if (sel) { sel.value = "healthy"; if (window.Endpoints) Endpoints.filterAndRender(); }
      });
    }

    const degradedCard = document.getElementById("kpiDegradedApis")?.closest(".stat-card");
    if (degradedCard) {
      degradedCard.style.cursor = "pointer";
      degradedCard.title = "Filter degraded APIs";
      degradedCard.addEventListener("click", () => {
        this.switchView("endpoints");
        const sel = document.getElementById("filterStatusSelect");
        if (sel) { sel.value = "degraded"; if (window.Endpoints) Endpoints.filterAndRender(); }
      });
    }

    const downCard = document.getElementById("kpiDownApis")?.closest(".stat-card");
    if (downCard) {
      downCard.style.cursor = "pointer";
      downCard.title = "View downtime incidents";
      downCard.addEventListener("click", () => this.switchView("incidents"));
    }

    const uptimeCard = document.getElementById("kpiGlobalUptime")?.closest(".stat-card");
    if (uptimeCard) {
      uptimeCard.style.cursor = "pointer";
      uptimeCard.title = "View latency & uptime analytics";
      uptimeCard.addEventListener("click", () => this.switchView("analytics"));
    }
  },

  initDemoSeeder() {
    const btnSeed = document.getElementById("btnSeedDemoApis");
    if (btnSeed) {
      btnSeed.addEventListener("click", async () => {
        btnSeed.disabled = true;
        btnSeed.innerHTML = `<span class="spinner"></span> Loading demo endpoints...`;

        const demoEndpoints = [
          {
            name: "HTTPBin Success (200 OK)",
            url: "https://httpbin.org/status/200",
            method: "GET",
            expected_status: 200,
            check_interval: 10,
            timeout: 10,
            tags: "demo,reliable"
          },
          {
            name: "GitHub API Root",
            url: "https://api.github.com",
            method: "GET",
            expected_status: 200,
            check_interval: 30,
            timeout: 10,
            tags: "demo,public-api"
          },
          {
            name: "JSONPlaceholder Posts",
            url: "https://jsonplaceholder.typicode.com/posts/1",
            method: "GET",
            expected_status: 200,
            check_interval: 30,
            timeout: 10,
            tags: "demo,rest"
          },
          {
            name: "HTTPBin Degraded Simulator (Delayed)",
            url: "https://httpbin.org/delay/2",
            method: "GET",
            expected_status: 200,
            check_interval: 60,
            timeout: 15,
            tags: "demo,slow"
          },
          {
            name: "HTTPBin Failure Simulator (500 Error)",
            url: "https://httpbin.org/status/500",
            method: "GET",
            expected_status: 200,
            check_interval: 30,
            timeout: 10,
            tags: "demo,outage-test"
          }
        ];

        let createdCount = 0;
        for (const ep of demoEndpoints) {
          try {
            const res = await fetch("/api/endpoints", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(ep)
            });
            if (res.ok) createdCount++;
          } catch (e) {
            console.error("Failed to seed endpoint:", ep.name, e);
          }
        }

        btnSeed.disabled = false;
        btnSeed.innerHTML = `<span>Load 5 Demo Test APIs</span>`;
        App.showToast("Demo APIs Loaded", `Successfully seeded ${createdCount} realistic test endpoints.`, "success");
        if (window.Analytics && Analytics.populateEndpointDropdown) {
          Analytics.populateEndpointDropdown();
        }
        App.switchView("dashboard");
      });
    }
  },

  async updateSidebarCounters(statsData = null) {
    try {
      let total = 0;
      let activeIncidents = 0;

      if (statsData && statsData.total_endpoints !== undefined) {
        total = statsData.total_endpoints;
        activeIncidents = statsData.active_incidents_count || 0;
      } else {
        const res = await fetch("/api/dashboard/stats");
        const json = await res.json();
        if (json.success && json.data) {
          total = json.data.total_endpoints;
          activeIncidents = json.data.active_incidents_count || 0;
        }
      }

      const countEl = document.getElementById("navEndpointCount");
      if (countEl) countEl.textContent = total;

      const incBadge = document.getElementById("navIncidentBadge");
      if (incBadge) {
        if (activeIncidents > 0) {
          incBadge.style.display = "inline-block";
          incBadge.textContent = activeIncidents;
        } else {
          incBadge.style.display = "none";
        }
      }
    } catch (err) {
      console.warn("Could not update sidebar counters:", err);
    }
  },

  /* -------------------------------------------------------------
     TOAST NOTIFICATIONS
     ------------------------------------------------------------- */
  showToast(title, message, type = "info", duration = 4000) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else if (type === "warning") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `
      <div class="toast-icon">${iconSvg}</div>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close-btn">&times;</button>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector(".toast-close-btn");
    closeBtn.addEventListener("click", () => toast.remove());

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.animation = "slideInRight 0.25s reverse forwards";
        setTimeout(() => toast.remove(), 250);
      }
    }, duration);
  },

  /* -------------------------------------------------------------
     FORMATTERS & HELPERS
     ------------------------------------------------------------- */
  parseUtcIso(isoString) {
    if (!isoString) return null;
    const s = String(isoString).trim();
    if (!s.endsWith("Z") && !s.includes("+") && !s.includes("-", 10)) {
      return new Date(s + "Z");
    }
    return new Date(s);
  },

  timeAgo(isoString) {
    if (!isoString) return "Never";
    const date = this.parseUtcIso(isoString);
    if (!date || isNaN(date.getTime())) return "Never";
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 5) return "Just now";
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  },

  formatTime(isoString) {
    if (!isoString) return "—";
    const date = this.parseUtcIso(isoString);
    if (!date || isNaN(date.getTime())) return "—";
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
};

// Explicitly attach to window for cross-file accessibility
window.App = App;

document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
