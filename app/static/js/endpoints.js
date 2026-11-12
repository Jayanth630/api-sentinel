/**
 * API SENTINEL - ENDPOINTS MANAGEMENT (CRUD, CHECKS, FILTERS)
 */

const Endpoints = {
  endpointsList: [],
  endpointToDeleteId: null,

  init() {
    this.initEvents();
  },

  initEvents() {
    // Open Add Modal
    const addBtn = document.getElementById("btnAddNewEndpoint");
    if (addBtn) addBtn.addEventListener("click", () => this.openModal());

    const emptyAddBtn = document.getElementById("btnEmptyAddEndpoint");
    if (emptyAddBtn) emptyAddBtn.addEventListener("click", () => this.openModal());

    // Modal Close
    const closeBtn = document.getElementById("btnCloseEndpointModal");
    const cancelBtn = document.getElementById("btnCancelEndpointModal");
    if (closeBtn) closeBtn.addEventListener("click", () => this.closeModal());
    if (cancelBtn) cancelBtn.addEventListener("click", () => this.closeModal());

    // Form Submit
    const form = document.getElementById("endpointForm");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.saveEndpoint();
      });
    }

    // Method selection change: show/hide request body field for GET/HEAD
    const methodSelect = document.getElementById("formMethod");
    const bodyGroup = document.getElementById("formBodyGroup");
    if (methodSelect && bodyGroup) {
      methodSelect.addEventListener("change", () => {
        const m = methodSelect.value;
        if (m === "GET" || m === "HEAD") {
          bodyGroup.style.display = "none";
        } else {
          bodyGroup.style.display = "flex";
        }
      });
    }

    // Header preset chips
    const presetChips = document.querySelectorAll(".preset-chip");
    presetChips.forEach(chip => {
      chip.addEventListener("click", () => {
        const headerJson = chip.getAttribute("data-header");
        const headersArea = document.getElementById("formHeaders");
        if (headersArea && headerJson) {
          try {
            let current = {};
            const existingText = headersArea.value.trim();
            if (existingText) {
              current = JSON.parse(existingText);
            }
            const incoming = JSON.parse(headerJson);
            const merged = { ...current, ...incoming };
            headersArea.value = JSON.stringify(merged, null, 2);
          } catch (e) {
            headersArea.value = headerJson;
          }
        }
      });
    });

    // Delete Modal Events
    const closeDeleteBtn = document.getElementById("btnCloseDeleteModal");
    const cancelDeleteBtn = document.getElementById("btnCancelDelete");
    const confirmDeleteBtn = document.getElementById("btnConfirmDelete");
    if (closeDeleteBtn) closeDeleteBtn.addEventListener("click", () => this.closeDeleteModal());
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener("click", () => this.closeDeleteModal());
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener("click", () => this.executeDelete());

    // Search and Filter Events
    const searchInput = document.getElementById("endpointSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", () => this.filterAndRender());
    }

    const filterStatus = document.getElementById("filterStatusSelect");
    if (filterStatus) {
      filterStatus.addEventListener("change", () => this.filterAndRender());
    }

    const filterMethod = document.getElementById("filterMethodSelect");
    if (filterMethod) {
      filterMethod.addEventListener("change", () => this.filterAndRender());
    }

    // Check All Button
    const checkAllBtn = document.getElementById("btnCheckAllNow");
    if (checkAllBtn) {
      checkAllBtn.addEventListener("click", () => this.checkAllEndpoints());
    }
  },

  async loadData() {
    try {
      const res = await fetch("/api/endpoints");
      const json = await res.json();
      if (json.success) {
        this.endpointsList = json.data;
        this.filterAndRender();
        // Immediately synchronize sidebar counters
        if (window.App && App.updateSidebarCounters) {
          App.updateSidebarCounters();
        }
      }
    } catch (err) {
      console.error("Failed to load endpoints:", err);
    }
  },

  filterAndRender() {
    const searchVal = (document.getElementById("endpointSearchInput")?.value || "").toLowerCase().trim();
    const statusVal = document.getElementById("filterStatusSelect")?.value || "";
    const methodVal = document.getElementById("filterMethodSelect")?.value || "";

    const filtered = this.endpointsList.filter(ep => {
      // Search match
      if (searchVal) {
        const matchesName = ep.name.toLowerCase().includes(searchVal);
        const matchesUrl = ep.url.toLowerCase().includes(searchVal);
        const matchesTags = (ep.tags || []).some(t => t.toLowerCase().includes(searchVal));
        if (!matchesName && !matchesUrl && !matchesTags) return false;
      }
      // Status match
      if (statusVal) {
        if (statusVal === "paused") {
          if (ep.is_active) return false;
        } else {
          if (!ep.is_active || ep.last_status !== statusVal) return false;
        }
      }
      // Method match
      if (methodVal && ep.method !== methodVal) {
        return false;
      }
      return true;
    });

    this.renderGrid(filtered);
  },

  renderGrid(endpoints) {
    const grid = document.getElementById("endpointsGrid");
    const emptyState = document.getElementById("endpointsEmptyState");
    if (!grid) return;

    if (!endpoints.length) {
      grid.innerHTML = "";
      if (emptyState) emptyState.style.display = "flex";
      return;
    }

    if (emptyState) emptyState.style.display = "none";

    grid.innerHTML = endpoints.map(ep => {
      const cardStatus = !ep.is_active ? "paused" : ep.last_status;
      const statusTitle = !ep.is_active ? "Paused" : (ep.last_status.charAt(0).toUpperCase() + ep.last_status.slice(1));
      
      const methodClass = `method-${ep.method.toLowerCase()}`;
      const statusClass = `status-badge ${cardStatus}`;

      const latencyDisplay = ep.last_response_time_ms !== null
        ? `${ep.last_response_time_ms} ms`
        : "—";

      const tagsHtml = (ep.tags || []).map(t => `<span class="tag-pill">${t}</span>`).join("");

      const errorBanner = (ep.last_status === "down" && ep.last_error_message)
        ? `<div class="card-error-banner"><strong>Outage:</strong> ${ep.last_error_message}</div>`
        : "";

      return `
        <div class="endpoint-card ${cardStatus}" id="endpoint-card-${ep.id}">
          <div class="card-header-row">
            <div class="card-title-group">
              <span class="method-badge ${methodClass}">${ep.method}</span>
              <span class="endpoint-name" title="${ep.name}">${ep.name}</span>
            </div>
            <span class="badge ${statusClass}">${statusTitle}</span>
          </div>

          <div class="endpoint-url-row">
            <span class="endpoint-url-text" title="${ep.url}">${ep.url}</span>
            <button class="copy-url-btn" onclick="Endpoints.copyUrl('${ep.url}')" title="Copy URL">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            </button>
          </div>

          <div class="card-metrics-grid">
            <div class="card-metric-item">
              <div class="metric-label">Uptime</div>
              <div class="metric-val" style="color: ${ep.uptime_percentage >= 99 ? 'var(--status-healthy)' : 'var(--status-degraded)'}">
                ${ep.uptime_percentage.toFixed(1)}%
              </div>
            </div>
            <div class="card-metric-item">
              <div class="metric-label">Latency</div>
              <div class="metric-val">${latencyDisplay}</div>
            </div>
            <div class="card-metric-item">
              <div class="metric-label">Last Checked</div>
              <div class="metric-val" style="font-size: 0.85rem; font-weight: 500;">
                ${App.timeAgo(ep.last_checked_at)}
              </div>
            </div>
          </div>

          ${errorBanner}

          <div class="card-tags-row">${tagsHtml}</div>

          <div class="card-actions-row">
            <div class="card-left-actions">
              <button class="btn btn-primary btn-sm check-btn" onclick="Endpoints.triggerCheck(${ep.id}, this)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                <span>Check Now</span>
              </button>
              <button class="btn btn-outline btn-sm" onclick="Endpoints.viewAnalytics(${ep.id})" title="Deep Dive Analytics">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                <span>Analytics</span>
              </button>
            </div>

            <div class="card-right-actions">
              <button class="btn btn-outline btn-sm btn-icon" onclick="Endpoints.toggleActive(${ep.id})" title="${ep.is_active ? 'Pause Monitoring' : 'Resume Monitoring'}">
                ${ep.is_active 
                  ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>` 
                  : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>`}
              </button>

              <button class="btn btn-outline btn-sm btn-icon" onclick="Endpoints.openEditModal(${ep.id})" title="Edit Configuration">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              </button>

              <button class="btn btn-danger btn-sm btn-icon" onclick="Endpoints.confirmDelete(${ep.id})" title="Delete Endpoint">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  },

  /* -------------------------------------------------------------
     ACTIONS: CHECK NOW & CHECK ALL
     ------------------------------------------------------------- */
  async triggerCheck(endpointId, btnElement) {
    if (btnElement) {
      btnElement.disabled = true;
      btnElement.innerHTML = `<span class="spinner"></span> Checking...`;
    }

    try {
      const res = await fetch(`/api/endpoints/${endpointId}/check`, { method: "POST" });
      const json = await res.json();

      if (json.success) {
        const cr = json.data.check_result;
        const msg = cr.is_success
          ? `HTTP ${cr.status_code} in ${cr.response_time_ms}ms`
          : (cr.error_message || "Check failed");

        App.showToast(
          `${json.data.endpoint.name} (${cr.status.toUpperCase()})`,
          msg,
          cr.status === "healthy" ? "success" : (cr.status === "degraded" ? "warning" : "error")
        );

        // Reload data to refresh UI
        this.loadData();
      } else {
        App.showToast("Check Failed", json.error || "Unable to reach endpoint", "error");
      }
    } catch (err) {
      App.showToast("Network Error", "Could not trigger health check.", "error");
    } finally {
      if (btnElement) {
        btnElement.disabled = false;
        btnElement.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg><span>Check Now</span>`;
      }
    }
  },

  async checkAllEndpoints() {
    const activeEps = this.endpointsList.filter(ep => ep.is_active);
    if (!activeEps.length) {
      App.showToast("No Active Endpoints", "Activate at least one API to perform health checks.", "info");
      return;
    }

    const checkBtn = document.getElementById("btnCheckAllNow");
    if (checkBtn) {
      checkBtn.disabled = true;
      checkBtn.innerHTML = `<span class="spinner"></span> Checking All...`;
    }

    let checkedCount = 0;
    for (const ep of activeEps) {
      try {
        await fetch(`/api/endpoints/${ep.id}/check`, { method: "POST" });
        checkedCount++;
      } catch (e) {
        console.error("Check error for ep:", ep.id, e);
      }
    }

    if (checkBtn) {
      checkBtn.disabled = false;
      checkBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><span>Check All</span>`;
    }

    App.showToast("Health Checks Complete", `Verified ${checkedCount} active endpoints in real time.`, "success");
    this.loadData();
  },

  async toggleActive(endpointId) {
    try {
      const res = await fetch(`/api/endpoints/${endpointId}/toggle`, { method: "POST" });
      const json = await res.json();
      if (json.success) {
        App.showToast("Status Updated", json.message, "info");
        this.loadData();
      }
    } catch (err) {
      App.showToast("Error", "Could not toggle endpoint state.", "error");
    }
  },

  viewAnalytics(endpointId) {
    if (window.Analytics) {
      Analytics.currentEndpointId = endpointId;
    }
    App.switchView("analytics");
  },

  copyUrl(url) {
    navigator.clipboard.writeText(url).then(() => {
      App.showToast("URL Copied", "Endpoint URL copied to clipboard.", "info", 2000);
    });
  },

  /* -------------------------------------------------------------
     MODAL CONTROLS & SAVE
     ------------------------------------------------------------- */
  openModal() {
    const modal = document.getElementById("endpointModal");
    const form = document.getElementById("endpointForm");
    const title = document.getElementById("modalEndpointTitle");
    const bodyGroup = document.getElementById("formBodyGroup");
    const saveBtn = document.getElementById("btnSaveEndpoint");

    if (form) form.reset();
    document.getElementById("formEndpointId").value = "";
    document.getElementById("formCheckInterval").value = "60";
    document.getElementById("formTimeout").value = "10";
    document.getElementById("formExpectedStatus").value = "200";
    if (bodyGroup) bodyGroup.style.display = "none";
    if (title) title.textContent = "Add Monitored API Endpoint";
    if (saveBtn) {
      const txt = saveBtn.querySelector(".btn-text");
      if (txt) txt.textContent = "Save & Monitor";
    }

    if (modal) modal.classList.add("active");
  },

  openEditModal(endpointId) {
    const ep = this.endpointsList.find(e => e.id === endpointId);
    if (!ep) return;

    this.openModal();
    document.getElementById("modalEndpointTitle").textContent = `Edit Endpoint: ${ep.name}`;
    document.getElementById("formEndpointId").value = ep.id;
    document.getElementById("formName").value = ep.name;
    document.getElementById("formUrl").value = ep.url;
    document.getElementById("formMethod").value = ep.method;
    document.getElementById("formExpectedStatus").value = ep.expected_status;
    document.getElementById("formTimeout").value = ep.timeout;
    document.getElementById("formCheckInterval").value = ep.check_interval;
    document.getElementById("formTags").value = (ep.tags || []).join(", ");
    
    // Format JSON nicely in textarea if valid
    let headersText = ep.raw_headers && ep.raw_headers !== "{}" ? ep.raw_headers : "";
    if (headersText) {
      try {
        headersText = JSON.stringify(JSON.parse(headersText), null, 2);
      } catch (e) {}
    }
    document.getElementById("formHeaders").value = headersText;
    document.getElementById("formBody").value = ep.body || "";

    const bodyGroup = document.getElementById("formBodyGroup");
    if (bodyGroup) {
      bodyGroup.style.display = (ep.method === "GET" || ep.method === "HEAD") ? "none" : "flex";
    }

    const saveBtn = document.getElementById("btnSaveEndpoint");
    if (saveBtn) {
      const txt = saveBtn.querySelector(".btn-text");
      if (txt) txt.textContent = "Save Changes";
    }
  },

  closeModal() {
    const modal = document.getElementById("endpointModal");
    if (modal) modal.classList.remove("active");
  },

  async saveEndpoint() {
    const saveBtn = document.getElementById("btnSaveEndpoint");
    const endpointId = document.getElementById("formEndpointId").value;
    const isEdit = Boolean(endpointId);
    const existingEp = isEdit ? this.endpointsList.find(e => e.id == endpointId) : null;

    const name = document.getElementById("formName").value.trim();
    const url = document.getElementById("formUrl").value.trim();
    const method = document.getElementById("formMethod").value;
    const expectedStatus = parseInt(document.getElementById("formExpectedStatus").value, 10);
    const timeout = parseInt(document.getElementById("formTimeout").value, 10);
    const checkInterval = parseInt(document.getElementById("formCheckInterval").value, 10);
    const tags = document.getElementById("formTags").value.trim();
    const headersRaw = document.getElementById("formHeaders").value.trim();
    const body = document.getElementById("formBody").value;

    const payload = {
      name,
      url,
      method,
      expected_status: isNaN(expectedStatus) ? 200 : expectedStatus,
      timeout: isNaN(timeout) ? 10 : timeout,
      check_interval: isNaN(checkInterval) ? 60 : checkInterval,
      tags,
      headers: headersRaw,
      body,
      // Preserve existing active status when editing so paused endpoints don't get unpaused
      is_active: existingEp ? existingEp.is_active : true
    };

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = `<span class="spinner"></span> Saving...`;
    }

    try {
      const endpointUrl = isEdit ? `/api/endpoints/${endpointId}` : "/api/endpoints";
      const httpMethod = isEdit ? "PUT" : "POST";

      const res = await fetch(endpointUrl, {
        method: httpMethod,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const json = await res.json();

      if (json.success) {
        this.closeModal();
        App.showToast("Success", json.message || "Endpoint saved.", "success");
        this.loadData();
      } else {
        App.showToast("Validation Error", json.error || "Could not save endpoint.", "error");
      }
    } catch (err) {
      App.showToast("Network Error", "Failed to communicate with server.", "error");
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span class="btn-text">${isEdit ? 'Save Changes' : 'Save & Monitor'}</span>`;
      }
    }
  },

  /* -------------------------------------------------------------
     DELETE CONTROLS
     ------------------------------------------------------------- */
  confirmDelete(endpointId) {
    this.endpointToDeleteId = endpointId;
    const ep = this.endpointsList.find(e => e.id === endpointId);
    const epName = ep ? ep.name : `Endpoint #${endpointId}`;
    const nameEl = document.getElementById("deleteEndpointName");
    if (nameEl) nameEl.textContent = epName;
    const modal = document.getElementById("deleteModal");
    if (modal) modal.classList.add("active");
  },

  closeDeleteModal() {
    this.endpointToDeleteId = null;
    const modal = document.getElementById("deleteModal");
    if (modal) modal.classList.remove("active");
  },

  async executeDelete() {
    if (!this.endpointToDeleteId) return;

    const confirmBtn = document.getElementById("btnConfirmDelete");
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = `<span class="spinner"></span> Deleting...`;
    }

    try {
      const res = await fetch(`/api/endpoints/${this.endpointToDeleteId}`, {
        method: "DELETE"
      });
      const json = await res.json();

      if (json.success) {
        this.closeDeleteModal();
        App.showToast("Deleted", json.message, "info");
        this.loadData();
      } else {
        App.showToast("Error", json.error || "Failed to delete endpoint", "error");
      }
    } catch (err) {
      App.showToast("Error", "Could not delete endpoint.", "error");
    } finally {
      if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Delete Endpoint";
      }
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Endpoints.init();
});
