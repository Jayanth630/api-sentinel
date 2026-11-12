/**
 * API SENTINEL - DASHBOARD CONTROLLER & CHART.JS ENGINE
 */

const Dashboard = {
  latencyChart: null,
  statusChart: null,

  async loadData() {
    try {
      const res = await fetch("/api/dashboard/stats");
      const json = await res.json();
      if (!json.success) {
        console.error("Dashboard error:", json.error);
        return;
      }
      const data = json.data;
      this.updateKpis(data);
      this.renderCharts(data);
      this.renderActivityFeed(data.recent_activity || []);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    }
  },

  updateKpis(data) {
    document.getElementById("kpiTotalApis").textContent = data.total_endpoints;
    document.getElementById("kpiActiveCount").textContent = data.active_endpoints;
    document.getElementById("kpiPausedCount").textContent = data.paused_endpoints;
    document.getElementById("kpiHealthyApis").textContent = data.healthy_count;
    document.getElementById("kpiDegradedApis").textContent = data.degraded_count;
    document.getElementById("kpiDownApis").textContent = data.down_count;
    document.getElementById("kpiIncidentsCount").textContent = data.active_incidents_count;
    document.getElementById("kpiAvgLatency").textContent = data.system_avg_latency;
    document.getElementById("kpiGlobalUptime").textContent = (data.system_uptime !== undefined ? data.system_uptime : 100.0).toFixed(1);
    document.getElementById("kpiTotalChecks").textContent = data.total_checks;

    // Instantly synchronize sidebar badge counts with single source of truth
    if (window.App && App.updateSidebarCounters) {
      App.updateSidebarCounters(data);
    }
  },

  renderCharts(data) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#9ca3af" : "#4b5563";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.06)";

    // Format trend labels in user's local timezone if ISO timestamps are available
    let labels = ["Waiting for checks..."];
    if (data.trend_timestamps && data.trend_timestamps.length) {
      labels = data.trend_timestamps.map(ts => App.formatTime(ts));
    } else if (data.trend_labels && data.trend_labels.length) {
      labels = data.trend_labels;
    }

    // 1. Latency Timeline Chart
    const ctxTrend = document.getElementById("chartLatencyTrend");
    if (ctxTrend && window.Chart) {
      if (this.latencyChart) {
        this.latencyChart.data.labels = labels;
        this.latencyChart.data.datasets[0].data = data.trend_latencies.length ? data.trend_latencies : [0];
        this.latencyChart.update();
      } else {
        this.latencyChart = new Chart(ctxTrend, {
          type: "line",
          data: {
            labels: labels,
            datasets: [{
              label: "Response Latency (ms)",
              data: data.trend_latencies.length ? data.trend_latencies : [0],
              borderColor: "#6366f1",
              backgroundColor: "rgba(99, 102, 241, 0.12)",
              fill: true,
              tension: 0.35,
              borderWidth: 2,
              pointRadius: 3,
              pointBackgroundColor: "#6366f1",
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
                displayColors: false,
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
    }

    // 2. Status Codes Doughnut Chart
    const ctxStatus = document.getElementById("chartStatusCodes");
    if (ctxStatus && window.Chart) {
      const dist = data.status_distribution || {};
      const statusLabels = ["2xx Success", "3xx Redirect", "4xx Client Err", "5xx Server Err", "Network Err"];
      const statusValues = [
        dist["2xx"] || 0,
        dist["3xx"] || 0,
        dist["4xx"] || 0,
        dist["5xx"] || 0,
        dist["Network_Error"] || 0
      ];

      // If all zeros, show placeholder
      const hasData = statusValues.some(v => v > 0);
      const displayData = hasData ? statusValues : [1];
      const displayColors = hasData ? [
        "#10b981", // 2xx Green
        "#3b82f6", // 3xx Blue
        "#f59e0b", // 4xx Amber
        "#ef4444", // 5xx Red
        "#6b7280"  // Network Error Slate
      ] : ["#374151"];

      if (this.statusChart) {
        this.statusChart.data.labels = hasData ? statusLabels : ["No pings recorded"];
        this.statusChart.data.datasets[0].data = displayData;
        this.statusChart.data.datasets[0].backgroundColor = displayColors;
        this.statusChart.update();
      } else {
        this.statusChart = new Chart(ctxStatus, {
          type: "doughnut",
          data: {
            labels: hasData ? statusLabels : ["No pings recorded"],
            datasets: [{
              data: displayData,
              backgroundColor: displayColors,
              borderWidth: 0,
              hoverOffset: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: {
              legend: {
                position: "bottom",
                labels: {
                  color: textColor,
                  boxWidth: 12,
                  font: { size: 11 },
                  padding: 12
                }
              },
              tooltip: {
                enabled: hasData,
                backgroundColor: isDark ? "#1f2937" : "#ffffff",
                titleColor: isDark ? "#f9fafb" : "#111827",
                bodyColor: isDark ? "#cbd5e1" : "#4b5563",
                borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
                borderWidth: 1,
                padding: 10
              }
            }
          }
        });
      }
    }
  },

  updateChartThemes() {
    if (this.latencyChart) {
      this.latencyChart.destroy();
      this.latencyChart = null;
    }
    if (this.statusChart) {
      this.statusChart.destroy();
      this.statusChart = null;
    }
    this.loadData();
  },

  renderActivityFeed(activity) {
    const tbody = document.getElementById("activityFeedBody");
    if (!tbody) return;

    if (!activity.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
            No check results recorded yet. Add an endpoint or run a health check to view the real-time activity stream.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = activity.map(item => {
      let statusBadge = "";
      if (item.is_success) {
        if (item.response_time_ms > 1200) {
          statusBadge = `<span class="badge status-badge degraded">Degraded</span>`;
        } else {
          statusBadge = `<span class="badge status-badge healthy">Healthy</span>`;
        }
      } else {
        statusBadge = `<span class="badge status-badge down">Failed</span>`;
      }

      const codeDisplay = item.status_code
        ? `<span style="font-weight: 700; font-family: monospace;">${item.status_code}</span>`
        : `<span style="color: var(--status-down); font-weight: 700; font-size: 0.8rem;">ERR</span>`;

      const latencyDisplay = `<span style="font-weight: 600;">${item.response_time_ms.toFixed(1)} ms</span>`;

      const outcomeText = item.is_success
        ? `<span style="color: var(--status-healthy); font-size: 0.8rem;">Response OK</span>`
        : `<span style="color: var(--status-down); font-size: 0.8rem;">${item.error_message || "Health check failed"}</span>`;

      return `
        <tr>
          <td>${statusBadge}</td>
          <td>
            <div style="font-weight: 600;">${item.endpoint_name}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.endpoint_url}</div>
          </td>
          <td>${codeDisplay}</td>
          <td>${latencyDisplay}</td>
          <td>${outcomeText}</td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${App.timeAgo(item.checked_at)}</td>
        </tr>
      `;
    }).join("");
  }
};

// Explicitly attach to window for cross-file accessibility
window.Dashboard = Dashboard;

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("btnRefreshFeed");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => Dashboard.loadData());
  }
});
