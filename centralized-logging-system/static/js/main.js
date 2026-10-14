/**
 * Centralized Logging System - Interactive Dashboard Controller
 * Handles live log fetching, client filtering, simulation triggers,
 * search highlighting, statistics updates, and detail modal inspection.
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        service: 'all',
        severity: 'all',
        search: '',
        autoRefresh: true,
        refreshIntervalMs: 3000,
        timerId: null,
        isFetching: false,
        cachedLogs: [],
    };

    // DOM Elements
    const elements = {
        // Stats
        statTotal: document.getElementById('stat-total'),
        statInfo: document.getElementById('stat-info'),
        statWarning: document.getElementById('stat-warning'),
        statError: document.getElementById('stat-error'),
        
        // Filter Controls
        filterService: document.getElementById('filter-service'),
        filterSeverity: document.getElementById('filter-severity'),
        filterSearch: document.getElementById('filter-search'),
        btnClearSearch: document.getElementById('btn-clear-search'),
        btnRefresh: document.getElementById('btn-refresh'),
        toggleAutorefresh: document.getElementById('toggle-autorefresh'),
        activeFiltersBar: document.getElementById('active-filters-bar'),
        filterChips: document.getElementById('filter-chips'),
        btnResetFilters: document.getElementById('btn-reset-filters'),
        
        // Cards
        cardFilterAll: document.getElementById('card-filter-all'),
        cardFilterInfo: document.getElementById('card-filter-info'),
        cardFilterWarning: document.getElementById('card-filter-warning'),
        cardFilterError: document.getElementById('card-filter-error'),

        // Table
        logsTbody: document.getElementById('logs-tbody'),
        logsCountBadge: document.getElementById('logs-count-badge'),
        loadingState: document.getElementById('loading-state'),
        emptyState: document.getElementById('empty-state'),
        emptyTitle: document.getElementById('empty-title'),
        emptySubtitle: document.getElementById('empty-subtitle'),
        btnEmptyReset: document.getElementById('btn-empty-reset'),

        // Actions
        btnExportCsv: document.getElementById('btn-export-csv'),
        btnClearLogs: document.getElementById('btn-clear-logs'),
        btnBatchDemo: document.getElementById('btn-batch-demo'),
        
        // Modal
        modal: document.getElementById('log-detail-modal'),
        modalClose: document.getElementById('modal-close'),
        modalDismissBtn: document.getElementById('modal-dismiss-btn'),
        modalCopyBtn: document.getElementById('modal-copy-btn'),
        modalSeverityBadge: document.getElementById('modal-severity-badge'),
        modalTimestamp: document.getElementById('modal-timestamp'),
        modalService: document.getElementById('modal-service'),
        modalSeverity: document.getElementById('modal-severity'),
        modalSource: document.getElementById('modal-source'),
        modalMessage: document.getElementById('modal-message'),

        // Toasts
        toastContainer: document.getElementById('toast-container'),
        liveStatusText: document.getElementById('live-status-text'),
    };

    let activeModalEntry = null;

    // -------------------------------------------------------------
    // Data Fetching
    // -------------------------------------------------------------
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) throw new Error('Stats network response not ok');
            const data = await res.json();
            if (data.status === 'success' && data.stats) {
                renderStats(data.stats);
            }
        } catch (err) {
            console.warn('Failed to update stats:', err);
        }
    }

    async function fetchLogs(showSpinner = false) {
        if (state.isFetching) return;
        state.isFetching = true;

        if (showSpinner) {
            elements.btnRefresh.querySelector('.refresh-spinner')?.classList.add('spinning');
        }

        try {
            const params = new URLSearchParams({
                service: state.service,
                severity: state.severity,
                search: state.search,
                limit: '200',
            });

            const res = await fetch(`/api/logs?${params.toString()}`);
            if (!res.ok) throw new Error('Logs fetch failed');
            const data = await res.json();

            if (data.status === 'success') {
                state.cachedLogs = data.logs || [];
                renderLogsTable(state.cachedLogs);
                renderActiveFilterChips();
            }
        } catch (err) {
            console.error('Error fetching logs:', err);
            showToast('Failed to connect to log server', 'error');
        } finally {
            state.isFetching = false;
            elements.btnRefresh.querySelector('.refresh-spinner')?.classList.remove('spinning');
        }
    }

    async function refreshAll(showSpinner = false) {
        await Promise.all([fetchStats(), fetchLogs(showSpinner)]);
    }

    // -------------------------------------------------------------
    // Render Functions
    // -------------------------------------------------------------
    function renderStats(stats) {
        animateValue(elements.statTotal, stats.total || 0);
        animateValue(elements.statInfo, stats.info || 0);
        animateValue(elements.statWarning, stats.warning || 0);
        animateValue(elements.statError, (stats.error || 0) + (stats.critical || 0));
    }

    function animateValue(element, target) {
        if (!element) return;
        const current = parseInt(element.textContent.replace(/,/g, ''), 10) || 0;
        if (current === target) {
            element.textContent = target.toLocaleString();
            return;
        }
        element.textContent = target.toLocaleString();
    }

    function highlightText(text, query) {
        if (!query || !query.trim()) return escapeHtml(text);
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return escapeHtml(text).replace(regex, '<mark class="search-highlight">$1</mark>');
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function renderLogsTable(logs) {
        elements.logsTbody.innerHTML = '';
        elements.logsCountBadge.textContent = `${logs.length} event${logs.length === 1 ? '' : 's'}`;

        if (logs.length === 0) {
            elements.emptyState.style.display = 'flex';
            if (state.service !== 'all' || state.severity !== 'all' || state.search) {
                elements.emptyTitle.textContent = 'No matching logs found';
                elements.emptySubtitle.textContent = 'Try resetting filters or expanding your search query.';
                elements.btnEmptyReset.style.display = 'inline-flex';
            } else {
                elements.emptyTitle.textContent = 'No logs collected yet';
                elements.emptySubtitle.textContent = 'Use the simulation deck above to generate sample events!';
                elements.btnEmptyReset.style.display = 'none';
            }
            return;
        }

        elements.emptyState.style.display = 'none';

        const fragment = document.createDocumentFragment();

        logs.forEach((log) => {
            const tr = document.createElement('tr');
            tr.className = `log-row log-${log.severity.toLowerCase()}`;

            // Severity Badge class
            let sevClass = 'badge-info';
            if (log.severity === 'WARNING') sevClass = 'badge-warning';
            else if (log.severity === 'ERROR' || log.severity === 'CRITICAL') sevClass = 'badge-error';

            // Service Badge class
            let svcClass = 'badge-service-login';
            if (log.service === 'payment_service' || log.service.includes('payment')) {
                svcClass = 'badge-service-payment';
            }

            const highlightedMsg = highlightText(log.message, state.search);

            tr.innerHTML = `
                <td class="col-time font-mono">${escapeHtml(log.timestamp)}</td>
                <td class="col-sev">
                    <span class="badge ${sevClass}">${escapeHtml(log.severity)}</span>
                </td>
                <td class="col-svc">
                    <span class="badge-service ${svcClass}">${escapeHtml(log.service)}</span>
                </td>
                <td class="col-msg">
                    <div class="log-message font-mono">${highlightedMsg}</div>
                </td>
                <td class="col-action">
                    <button class="btn-inspect" title="Inspect log event">Inspect</button>
                </td>
            `;

            tr.querySelector('.btn-inspect').addEventListener('click', () => {
                openInspectModal(log);
            });

            fragment.appendChild(tr);
        });

        elements.logsTbody.appendChild(fragment);
    }

    function renderActiveFilterChips() {
        const chips = [];
        if (state.service !== 'all') {
            chips.push({ key: 'service', label: `Service: ${state.service}` });
        }
        if (state.severity !== 'all') {
            chips.push({ key: 'severity', label: `Severity: ${state.severity}` });
        }
        if (state.search.trim()) {
            chips.push({ key: 'search', label: `Search: "${state.search}"` });
        }

        if (chips.length > 0) {
            elements.activeFiltersBar.style.display = 'flex';
            elements.filterChips.innerHTML = chips.map(c => `
                <div class="filter-chip" data-key="${c.key}">
                    <span>${escapeHtml(c.label)}</span>
                    <span class="chip-remove">&times;</span>
                </div>
            `).join('');

            elements.filterChips.querySelectorAll('.filter-chip').forEach(chip => {
                chip.querySelector('.chip-remove').addEventListener('click', () => {
                    const key = chip.dataset.key;
                    if (key === 'service') {
                        state.service = 'all';
                        elements.filterService.value = 'all';
                    } else if (key === 'severity') {
                        state.severity = 'all';
                        elements.filterSeverity.value = 'all';
                    } else if (key === 'search') {
                        state.search = '';
                        elements.filterSearch.value = '';
                        elements.btnClearSearch.style.display = 'none';
                    }
                    refreshAll(true);
                });
            });
        } else {
            elements.activeFiltersBar.style.display = 'none';
            elements.filterChips.innerHTML = '';
        }
    }

    // -------------------------------------------------------------
    // Simulation Generator Trigger
    // -------------------------------------------------------------
    async function triggerSimulation(service, eventType) {
        showToast(`Simulating ${service} event: ${eventType}...`, 'info');

        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    service: service,
                    event_type: eventType,
                }),
            });

            if (!res.ok) throw new Error('Simulation failed');
            const data = await res.json();

            if (data.status === 'success') {
                const toastType = eventType.includes('timeout') || eventType.includes('error') 
                    ? 'error' 
                    : (eventType.includes('warning') || eventType.includes('fail') ? 'warning' : 'success');
                
                showToast(`[${service}] Event generated: ${eventType}`, toastType);
                await refreshAll(true);
            }
        } catch (err) {
            console.error('Simulation error:', err);
            showToast('Failed to simulate service event', 'error');
        }
    }

    // -------------------------------------------------------------
    // Toast Notification System
    // -------------------------------------------------------------
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ';
        if (type === 'success') icon = '✓';
        if (type === 'warning') icon = '⚠';
        if (type === 'error') icon = '✕';

        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // -------------------------------------------------------------
    // Detail Modal Inspection
    // -------------------------------------------------------------
    function openInspectModal(log) {
        activeModalEntry = log;
        elements.modalTimestamp.textContent = log.timestamp;
        elements.modalService.textContent = log.service;
        elements.modalSeverity.textContent = log.severity;
        elements.modalSource.textContent = log.source_file;
        elements.modalMessage.textContent = log.message;

        elements.modalSeverityBadge.className = `badge badge-${log.severity.toLowerCase()}`;
        elements.modalSeverityBadge.textContent = log.severity;

        elements.modal.style.display = 'flex';
    }

    function closeModal() {
        elements.modal.style.display = 'none';
        activeModalEntry = null;
    }

    // -------------------------------------------------------------
    // Event Listeners
    // -------------------------------------------------------------
    
    // Service filter change
    elements.filterService.addEventListener('change', (e) => {
        state.service = e.target.value;
        refreshAll(true);
    });

    // Severity filter change
    elements.filterSeverity.addEventListener('change', (e) => {
        state.severity = e.target.value;
        refreshAll(true);
    });

    // Search input (debounced)
    let searchDebounceTimeout;
    elements.filterSearch.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.btnClearSearch.style.display = val.length > 0 ? 'block' : 'none';

        clearTimeout(searchDebounceTimeout);
        searchDebounceTimeout = setTimeout(() => {
            state.search = val;
            refreshAll(false);
        }, 250);
    });

    elements.btnClearSearch.addEventListener('click', () => {
        elements.filterSearch.value = '';
        state.search = '';
        elements.btnClearSearch.style.display = 'none';
        refreshAll(true);
    });

    // Refresh button
    elements.btnRefresh.addEventListener('click', () => {
        refreshAll(true);
    });

    // Metric Cards quick filter
    elements.cardFilterAll.addEventListener('click', () => {
        state.severity = 'all';
        elements.filterSeverity.value = 'all';
        refreshAll(true);
    });

    elements.cardFilterInfo.addEventListener('click', () => {
        state.severity = 'INFO';
        elements.filterSeverity.value = 'INFO';
        refreshAll(true);
    });

    elements.cardFilterWarning.addEventListener('click', () => {
        state.severity = 'WARNING';
        elements.filterSeverity.value = 'WARNING';
        refreshAll(true);
    });

    elements.cardFilterError.addEventListener('click', () => {
        state.severity = 'ERROR';
        elements.filterSeverity.value = 'ERROR';
        refreshAll(true);
    });

    // Reset filters buttons
    elements.btnResetFilters.addEventListener('click', resetAllFilters);
    elements.btnEmptyReset.addEventListener('click', resetAllFilters);

    function resetAllFilters() {
        state.service = 'all';
        state.severity = 'all';
        state.search = '';
        elements.filterService.value = 'all';
        elements.filterSeverity.value = 'all';
        elements.filterSearch.value = '';
        elements.btnClearSearch.style.display = 'none';
        refreshAll(true);
    }

    // Auto-refresh toggle
    elements.toggleAutorefresh.addEventListener('change', (e) => {
        state.autoRefresh = e.target.checked;
        if (state.autoRefresh) {
            startAutoRefresh();
            elements.liveStatusText.textContent = 'Live Ingestion';
            showToast('Auto-refresh activated (3s)', 'info');
        } else {
            stopAutoRefresh();
            elements.liveStatusText.textContent = 'Paused';
            showToast('Auto-refresh paused', 'info');
        }
    });

    function startAutoRefresh() {
        stopAutoRefresh();
        state.timerId = setInterval(() => {
            if (state.autoRefresh && document.visibilityState === 'visible') {
                refreshAll(false);
            }
        }, state.refreshIntervalMs);
    }

    function stopAutoRefresh() {
        if (state.timerId) {
            clearInterval(state.timerId);
            state.timerId = null;
        }
    }

    // Simulation Buttons
    document.querySelectorAll('.btn-sim').forEach((btn) => {
        btn.addEventListener('click', () => {
            const service = btn.dataset.service;
            const eventType = btn.dataset.event;
            if (service && eventType) {
                triggerSimulation(service, eventType);
            }
        });
    });

    // Populate Batch Demo Traffic
    elements.btnBatchDemo.addEventListener('click', async () => {
        showToast('Injecting multi-service demonstration traffic...', 'info');
        try {
            await Promise.all([
                fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'login', event_type: 'success' }),
                }),
                fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'payment', event_type: 'success' }),
                }),
                fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'login', event_type: 'invalid_credentials' }),
                }),
                fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'payment', event_type: 'timeout' }),
                }),
                fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'login', event_type: 'warning' }),
                }),
            ]);
            showToast('Demo traffic generated across Login & Payment services!', 'success');
            await refreshAll(true);
        } catch (err) {
            console.error('Batch generation failed:', err);
        }
    });

    // Clear Logs
    elements.btnClearLogs.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all log files? This will reset the demo data.')) {
            return;
        }

        try {
            const res = await fetch('/api/clear', { method: 'POST' });
            if (res.ok) {
                showToast('All service log files have been reset.', 'info');
                await refreshAll(true);
            }
        } catch (err) {
            showToast('Failed to clear logs', 'error');
        }
    });

    // Export CSV
    elements.btnExportCsv.addEventListener('click', () => {
        const params = new URLSearchParams({
            format: 'csv',
            service: state.service,
            severity: state.severity,
            search: state.search,
        });
        window.location.href = `/api/export?${params.toString()}`;
    });

    // Modal Close
    elements.modalClose.addEventListener('click', closeModal);
    elements.modalDismissBtn.addEventListener('click', closeModal);
    elements.modal.addEventListener('click', (e) => {
        if (e.target === elements.modal) closeModal();
    });

    // Copy event details
    elements.modalCopyBtn.addEventListener('click', () => {
        if (!activeModalEntry) return;
        const text = `[${activeModalEntry.timestamp}] [${activeModalEntry.severity}] [${activeModalEntry.service}] ${activeModalEntry.message}`;
        navigator.clipboard.writeText(text).then(() => {
            showToast('Event copied to clipboard', 'success');
        }).catch(() => {
            showToast('Could not copy to clipboard', 'warning');
        });
    });

    // -------------------------------------------------------------
    // Initialization
    // -------------------------------------------------------------
    refreshAll(true);
    startAutoRefresh();
});
