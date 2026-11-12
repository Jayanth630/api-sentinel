/**
 * API SENTINEL - INCIDENTS CONTROLLER
 */

const Incidents = {
  init() {
    const filterSelect = document.getElementById("filterIncidentState");
    if (filterSelect) {
      filterSelect.addEventListener("change", () => this.loadData());
    }
  },

  async loadData() {
    const filterSelect = document.getElementById("filterIncidentState");
    const activeVal = filterSelect ? filterSelect.value : "";
    const url = activeVal !== "" ? `/api/incidents?active=${activeVal}` : "/api/incidents";

    try {
      const res = await fetch(url);
      const json = await res.json();
      if (!json.success) return;

      this.renderTable(json.data);
    } catch (err) {
      console.error("Failed to load incidents:", err);
    }
  },

  renderTable(incidents) {
    const tbody = document.getElementById("incidentsTableBody");
    if (!tbody) return;

    if (!incidents.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
            No incidents recorded. All systems are operating normally.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = incidents.map(inc => {
      const stateBadge = inc.is_active
        ? `<span class="badge status-badge down" style="animation: pulse-ring 2s infinite;">Active Outage</span>`
        : `<span class="badge status-badge healthy">Resolved</span>`;

      let durationText = "—";
      if (inc.duration_seconds) {
        const mins = Math.floor(inc.duration_seconds / 60);
        const secs = inc.duration_seconds % 60;
        durationText = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      } else if (inc.is_active && inc.started_at) {
        const startDate = (window.App && App.parseUtcIso) ? App.parseUtcIso(inc.started_at) : new Date(inc.started_at);
        const elapsedSecs = Math.max(0, Math.floor((new Date() - startDate) / 1000));
        const mins = Math.floor(elapsedSecs / 60);
        const secs = elapsedSecs % 60;
        durationText = mins > 0 ? `${mins}m ${secs}s (Ongoing)` : `${secs}s (Ongoing)`;
      }

      const statusDisplay = inc.last_status_code
        ? `<span style="font-weight: 700; font-family: monospace;">HTTP ${inc.last_status_code}</span>`
        : `<span style="color: var(--status-down); font-weight: 600;">Network / Timeout</span>`;

      const startedDate = (window.App && App.parseUtcIso) ? App.parseUtcIso(inc.started_at) : new Date(inc.started_at);
      const resolvedDate = inc.resolved_at ? ((window.App && App.parseUtcIso) ? App.parseUtcIso(inc.resolved_at) : new Date(inc.resolved_at)) : null;

      return `
        <tr>
          <td>${stateBadge}</td>
          <td>
            <div style="font-weight: 700;">${inc.endpoint_name}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${inc.endpoint_url}</div>
          </td>
          <td>${startedDate ? startedDate.toLocaleString() : '—'}</td>
          <td>${resolvedDate ? resolvedDate.toLocaleString() : `<span style="color: var(--status-down); font-weight: 600;">Unresolved</span>`}</td>
          <td style="font-weight: 600;">${durationText}</td>
          <td>${statusDisplay}</td>
          <td style="color: var(--status-down); font-size: 0.8rem; word-break: break-word;">${inc.error_message}</td>
        </tr>
      `;
    }).join("");
  }
};

// Explicitly attach to window for cross-file accessibility
window.Incidents = Incidents;

document.addEventListener("DOMContentLoaded", () => {
  Incidents.init();
});
