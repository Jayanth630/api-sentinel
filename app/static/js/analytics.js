/**
 * API SENTINEL - DEEP-DIVE ANALYTICS CONTROLLER
 */

const Analytics = {
  currentEndpointId: null,
  currentTimeframeHours: 24,
  historyChart: null,

  init() {
    this.initEvents();
  },

  initEvents() {
    const epSelect = document.getElementById("analyticsEndpointSelect");
    if (epSelect) {
      epSelect.addEventListener("change", (e) => {
        this.currentEndpointId = e.target.value ? parseInt(e.target.value, 10) : null;
        this.loadEndpointAnalytics();
      });
    }

    // Timeframe buttons
    const timeframeBtns = document.querySelectorAll("#viewAnalytics [data-hours]");
    timeframeBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        timeframeBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentTimeframeHours = parseInt(btn.getAttribute("data-hours"), 10);
        this.loadEndpointAnalytics();
      });
    });
  },

  async loadData() {
    await this.populateEndpointDropdown();
    await this.loadEndpointAnalytics();
    await this.loadComparisonTable();
  },

  async populateEndpointDropdown() {
    const sel = document.getElementById("analyticsEndpointSelect");
    if (!sel) return;

    try {
      const res = await fetch("/api/endpoints");
      const json = await res.json();
      if (!json.success) return;

      const endpoints = json.data;
      if (!endpoints.length) {
        sel.innerHTML = `<option value="">No endpoints configured</option>`;
        this.currentEndpointId = null;
        return;
      }

      // Check if options changed to prevent tearing down active user interaction
      const currentIds = Array.from(sel.options).map(o => o.value).filter(Boolean).join(",");
      const newIds = endpoints.map(e => String(e.id)).join(",");

      if (currentIds !== newIds || sel.options.length === 0) {
        sel.innerHTML = endpoints.map(ep => `
          <option value="${ep.id}" ${this.currentEndpointId === ep.id ? "selected" : ""}>
            ${ep.name} (${ep.method} - ${ep.url})
          </option>
        `).join("");
      }

      // If no endpoint is selected, select the first one
      if (!this.currentEndpointId && endpoints.length > 0) {
        this.currentEndpointId = endpoints[0].id;
      }

      if (this.currentEndpointId) {
        sel.value = this.currentEndpointId;
      }
    } catch (err) {
      console.error("Error populating endpoint selector:", err);
    }
  },

  selectEndpoint(endpointId) {
    this.currentEndpointId = endpointId;
    const sel = document.getElementById("analyticsEndpointSelect");
    if (sel) sel.value = endpointId;
    this.loadEndpointAnalytics();
  },

  async loadEndpointAnalytics() {
    if (!this.currentEndpointId) return;

    try {
      const res = await fetch(`/api/analytics/endpoint/${this.currentEndpointId}?hours=${this.currentTimeframeHours}`);
      const json = await res.json();
      if (!json.success) return;

      const d = json.data;
      this.updateAnalyticsKpis(d);
      this.renderHistoryChart(d);
    } catch (err) {
      console.error("Failed to load endpoint analytics:", err);
    }
  },

  updateAnalyticsKpis(d) {
    document.getElementById("anaUptime").textContent = `${(d.uptime_percentage !== undefined ? d.uptime_percentage : 100).toFixed(1)}%`;
    document.getElementById("anaSuccessfulChecks").textContent = d.successful_checks;
    document.getElementById("anaTotalChecks").textContent = d.total_checks;
    document.getElementById("anaAvgLatency").textContent = d.avg_latency_ms;
    document.getElementById("anaMinLatency").textContent = d.min_latency_ms;
    document.getElementById("anaMaxLatency").textContent = d.max_latency_ms;
    document.getElementById("anaP95Latency").textContent = d.p95_latency_ms;
    document.getElementById("anaFailures").textContent = d.failed_checks;

    const subtitleEl = document.getElementById("anaChartSubtitle");
    if (subtitleEl && d.endpoint) {
      subtitleEl.textContent = `${d.endpoint.name} (${d.endpoint.method} ${d.endpoint.url}) - Last ${d.timeframe_hours} hours`;
    }
  },

  renderHistoryChart(d) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#9ca3af" : "#4b5563";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.06)";

    const ctx = document.getElementById("chartEndpointHistory");
    if (!ctx || !window.Chart) return;

    const labels = (d.history || []).map(h => {
      if (h.iso_timestamp && window.App && App.parseUtcIso) {
        const dt = App.parseUtcIso(h.iso_timestamp);
        if (dt && !isNaN(dt.getTime())) {
          if (d.timeframe_hours > 24) {
            return dt.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          }
          return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
      }
      return h.timestamp;
    });
    const dataPoints = (d.history || []).map(h => h.latency_ms);
    const pointColors = (d.history || []).map(h => h.is_success ? "#6366f1" : "#ef4444");

    const displayLabels = labels.length ? labels : ["No data yet"];
    const displayData = dataPoints.length ? dataPoints : [0];

    if (this.historyChart) {
      this.historyChart.data.labels = displayLabels;
      this.historyChart.data.datasets[0].data = displayData;
      this.historyChart.data.datasets[0].pointBackgroundColor = pointColors.length ? pointColors : "#6366f1";
      this.historyChart.update();
    } else {
      this.historyChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: displayLabels,
          datasets: [{
            label: "Latency (ms)",
            data: displayData,
            borderColor: "#6366f1",
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            fill: true,
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: pointColors.length ? pointColors : "#6366f1",
            pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: isDark ? "#1f2937" : "#ffffff",
              titleColor: isDark ? "#f9fafb" : "#111827",
              bodyColor: isDark ? "#cbd5e1" : "#4b5563",
              borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
              borderWidth: 1,
              padding: 10,
              callbacks: {
                label: (ctx) => ` Latency: ${ctx.parsed.y} ms`
              }
            }
          },
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { size: 11 } }
            },
            y: {
              beginAtZero: true,
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                font: { size: 11 },
                callback: (val) => `${val}ms`
              }
            }
          }
        }
      });
    }
  },

  async loadComparisonTable() {
    const tbody = document.getElementById("comparisonTableBody");
    if (!tbody) return;

    try {
      const res = await fetch("/api/analytics/comparison");
      const json = await res.json();
      if (!json.success) return;

      const endpoints = json.data;
      if (!endpoints.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
              No endpoints available to compare. Add endpoints to view comparative benchmarks.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = endpoints.map(ep => {
        const methodClass = `method-${ep.method.toLowerCase()}`;
        const statusClass = `status-badge ${!ep.is_active ? 'paused' : ep.last_status}`;
        const statusTitle = !ep.is_active ? 'Paused' : ep.last_status;

        return `
          <tr>
            <td>
              <div style="font-weight: 700;">${ep.name}</div>
              <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${ep.url}</div>
            </td>
            <td><span class="method-badge ${methodClass}">${ep.method}</span></td>
            <td><span class="badge ${statusClass}">${statusTitle}</span></td>
            <td style="font-weight: 700; color: ${ep.uptime_percentage >= 99 ? 'var(--status-healthy)' : 'var(--status-degraded)'}">
              ${ep.uptime_percentage.toFixed(1)}%
            </td>
            <td style="font-weight: 600;">${ep.avg_latency_ms} ms</td>
            <td style="color: ${ep.failure_rate > 5 ? 'var(--status-down)' : 'var(--text-secondary)'}; font-weight: 600;">
              ${ep.failure_rate.toFixed(1)}%
            </td>
            <td>${ep.total_checks}</td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      console.error("Error loading comparison table:", err);
    }
  },

  updateChartThemes() {
    if (this.historyChart) {
      this.historyChart.destroy();
      this.historyChart = null;
    }
    this.loadEndpointAnalytics();
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Analytics.init();
});
