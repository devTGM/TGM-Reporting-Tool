// TGM Reporting Studio Frontend Application Logic
let currentClientId = "";
let clientsList = [];
let currentUser = null;

// API Client Helper with Session Token Injection
async function api(endpoint, options = {}) {
  try {
    const token = localStorage.getItem('tgm_session_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };
    const res = await fetch(endpoint, {
      ...options,
      headers
    });
    if (res.status === 401 && !endpoint.includes('/api/auth/login')) {
      localStorage.removeItem('tgm_session_token');
      currentUser = null;
      updateHeaderUserProfile(null);
      openModal('modal-login');
      throw new Error('Authentication required. Please sign in.');
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'API Request failed');
    }
    return await res.json();
  } catch (error) {
    console.error('API Error:', error);
    showToast(error.message, 'error');
    throw error;
  }
}


// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Active Global Currency (Defaults to Indian Rupee INR ₹)
let currentCurrency = localStorage.getItem('tgm_currency') || 'INR';

const CURRENCY_SYMBOLS = {
  'INR': '₹',
  'USD': '$',
  'EUR': '€',
  'GBP': '£',
  'AED': 'AED ',
  'CAD': 'CA$',
  'AUD': 'AU$'
};

function getCurrencySymbol(curr = currentCurrency) {
  return CURRENCY_SYMBOLS[(curr || currentCurrency).toUpperCase()] || '₹';
}

// Format Currency dynamically
function formatCurrency(val, currency = currentCurrency) {
  const num = Number(val) || 0;
  const curr = (currency || currentCurrency).toUpperCase();
  const sym = getCurrencySymbol(curr);
  
  if (curr === 'INR') {
    return sym + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return sym + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Format Number
function formatNumber(val) {
  const num = Number(val) || 0;
  return num.toLocaleString();
}

// Tab Navigation
function setupNavigation() {
  const buttons = document.querySelectorAll('.nav-tab-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(targetId);
      if (activePane) activePane.classList.add('active');

      // Trigger redraw of charts or data if switched
      if (targetId === 'tab-dashboard') {
        loadDashboardData();
      } else if (targetId === 'tab-clients') {
        loadClients();
      } else if (targetId === 'tab-data') {
        loadCleanedRecords();
      } else if (targetId === 'tab-bigquery') {
        loadBigQueryConfig();
      } else if (targetId === 'tab-looker') {
        loadLookerResources();
      } else if (targetId === 'tab-team') {
        loadTeamUsers();
      }
    });
  });
}

// Modal Handlers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    modal.style.display = 'flex';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
}
window.openModal = openModal;
window.closeModal = closeModal;

// Setup Sync Modal Defaults
function setupSyncModal() {
  const today = new Date().toISOString().slice(0, 10);
  const twoWeeksAgo = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);

  const startInput = document.getElementById('sync-start-date');
  const endInput = document.getElementById('sync-end-date');
  if (startInput) startInput.value = twoWeeksAgo;
  if (endInput) endInput.value = today;

  const openBtn = document.getElementById('btn-open-sync-modal');
  if (openBtn) {
    openBtn.addEventListener('click', () => openModal('modal-sync'));
  }

  const startSyncBtn = document.getElementById('btn-start-sync');
  if (startSyncBtn) {
    startSyncBtn.addEventListener('click', handleExecuteSync);
  }
}

// Load Clients and Populate Select Dropdown
async function loadClients() {
  try {
    clientsList = await api('/api/clients');
    const select = document.getElementById('global-client-select');
    if (select) {
      select.innerHTML = '';
      const isAdmin = currentUser && currentUser.role === 'admin';
      
      // Admins get blended all clients view option; non-admins are restricted to their assigned accounts
      if (isAdmin) {
        const allOpt = document.createElement('option');
        allOpt.value = '';
        allOpt.textContent = 'All Agency Clients (Blended)';
        select.appendChild(allOpt);
      }

      clientsList.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = `${c.name} (${c.currency})`;
        select.appendChild(opt);
      });

      // Enforce selection for restricted members
      if (!isAdmin && clientsList.length > 0) {
        if (!currentClientId || !clientsList.find(c => c.id === currentClientId)) {
          currentClientId = clientsList[0].id;
        }
        select.value = currentClientId;
      } else {
        select.value = currentClientId;
      }
    }

    const sheetClientSelect = document.getElementById('sheets-sync-client');
    if (sheetClientSelect) {
      const prevVal = sheetClientSelect.value;
      sheetClientSelect.innerHTML = '';
      clientsList.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = `${c.name} (${c.currency})${c.google_sheet_url ? ' 🟢' : ' ⚪'}`;
        sheetClientSelect.appendChild(opt);
      });
      if (prevVal && clientsList.some(c => c.id === prevVal)) {
        sheetClientSelect.value = prevVal;
      } else if (currentClientId && clientsList.some(c => c.id === currentClientId)) {
        sheetClientSelect.value = currentClientId;
      }
      onSheetsSyncClientChanged();
    }

    renderClientsTab();
  } catch (err) {
    console.error('Failed to load clients:', err);
  }
}

// Render Clients Grid in Clients Tab
function renderClientsTab() {
  const grid = document.getElementById('clients-card-grid');
  if (!grid) return;

  grid.innerHTML = '';
  clientsList.forEach(c => {
    const card = document.createElement('div');
    card.className = 'card';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.justifyContent = 'space-between';
    card.style.border = '1px solid rgba(255, 255, 255, 0.08)';
    card.style.background = 'linear-gradient(135deg, rgba(20, 10, 40, 0.6) 0%, rgba(10, 4, 22, 0.95) 100%)';

    const roas = c.total_spend > 0 ? (c.total_revenue / c.total_spend).toFixed(2) : '0.00';
    const roasBadge = parseFloat(roas) >= 2.0 ? 'tier-high' : (parseFloat(roas) >= 1.0 ? 'tier-mid' : 'tier-low');
    const isAdmin = currentUser && currentUser.role === 'admin';

    const sheetSectionHtml = c.google_sheet_url
      ? `
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 0.5rem 0.65rem; margin-bottom: 0.85rem; font-size: 0.74rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
            <span style="color: var(--accent-emerald-light); font-weight: 700; display: flex; align-items: center; gap: 0.35rem;">
              <span>📊</span> Dedicated Sheet Linked
            </span>
            <a href="${c.google_sheet_url}" target="_blank" style="color: var(--accent-cyan); text-decoration: none; font-size: 0.7rem; font-weight: 600;">
              Open Sheet &rarr;
            </a>
          </div>
          <div style="color: var(--text-muted); font-size: 0.68rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            GID: <strong style="color: #cbd5e1;">${c.google_sheet_gid || '0'}</strong> &bull; ${c.last_sheet_synced_at ? `Synced ${formatRelativeTime(c.last_sheet_synced_at)}` : 'Ready to sync'}
          </div>
        </div>
      `
      : `
        <div style="background: rgba(245, 158, 11, 0.08); border: 1px dashed rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 0.45rem 0.65rem; margin-bottom: 0.85rem; font-size: 0.74rem; display: flex; justify-content: space-between; align-items: center;">
          <span style="color: #fbbf24; font-weight: 600;">⚠️ No Sheet Linked</span>
          <button class="btn btn-secondary btn-sm" onclick="openEditClientModal('${c.id}')" style="padding: 0.2rem 0.5rem; font-size: 0.68rem;">+ Link Sheet</button>
        </div>
      `;

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
          <div>
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 0.2rem;">${c.name}</h3>
            <p style="font-size: 0.75rem; color: var(--text-muted);">${c.industry} &bull; <span style="color: var(--tgm-flame-light); font-weight: 600;">${c.currency} (${getCurrencySymbol(c.currency)})</span></p>
          </div>
          <span class="status-dot ${c.is_active ? 'active' : 'warning'}" title="${c.is_active ? 'Active' : 'Paused'}"></span>
        </div>
        
        <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
          <a href="${c.website || '#'}" target="_blank" style="color: var(--accent-indigo); text-decoration: none; word-break: break-all;">${c.website || 'No website registered'}</a>
        </p>

        <!-- Dedicated Google Sheet Source Badge -->
        ${sheetSectionHtml}

        <!-- Client Live Metrics Snapshot -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; background: rgba(0, 0, 0, 0.3); padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid rgba(255, 255, 255, 0.05);">
          <div>
            <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Spend</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: #fff;">${formatCurrency(c.total_spend, c.currency)}</div>
          </div>
          <div>
            <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Revenue</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: var(--accent-emerald-light);">${formatCurrency(c.total_revenue, c.currency)}</div>
          </div>
          <div style="margin-top: 0.25rem;">
            <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">ROAS</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #FFCD57;">${roas}x</div>
          </div>
          <div style="margin-top: 0.25rem;">
            <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Ingested Rows</div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #cbd5e1;">${formatNumber(c.total_records)}</div>
          </div>
        </div>
      </div>
      
      <div style="display: flex; gap: 0.35rem; flex-wrap: wrap; border-top: 1px solid var(--border-color); padding-top: 0.75rem;">
        <button class="btn btn-primary btn-sm" style="flex: 1; padding: 0.35rem 0.5rem;" onclick="selectClientAndSwitch('${c.id}')">Dashboard</button>
        <button class="btn btn-secondary btn-sm" onclick="openSharePortalModal('${c.id}', '${c.name.replace(/'/g, "\\'")}')" title="Share Real-Time Live Dashboard with Client (Zero Login)" style="border-color: rgba(16, 185, 129, 0.4); color: var(--accent-emerald-light); padding: 0.35rem 0.5rem;">
          Portal
        </button>
        <button class="btn btn-secondary btn-sm" id="btn-sync-card-${c.id}" onclick="syncClientSheetDirectly('${c.id}', this)" title="Sync this client's Google Sheet directly" style="color: var(--accent-cyan); padding: 0.35rem 0.5rem;">
          Sync Sheet
        </button>
        <button class="btn btn-secondary btn-sm" onclick="openEditClientModal('${c.id}')" title="Configure Google Sheet & Client Details" style="padding: 0.35rem 0.5rem;">
          Configure
        </button>
        ${isAdmin ? `<button class="btn btn-outline btn-sm" onclick="handleDeleteClient('${c.id}')" title="Delete Client" style="color: var(--tgm-crimson); padding: 0.35rem 0.5rem;">&#128465;</button>` : ''}
      </div>
    `;
    grid.appendChild(card);
  });
}

function openSyncForClient(clientId) {
  const sheetClientSelect = document.getElementById('sheets-sync-client');
  if (sheetClientSelect) {
    sheetClientSelect.value = clientId;
    onSheetsSyncClientChanged();
  }
  
  // Switch to Platform Connectors tab
  const connectorsTabBtn = document.querySelector('[data-tab="tab-connectors"]');
  if (connectorsTabBtn) connectorsTabBtn.click();
  
  const client = clientsList.find(c => c.id === clientId);
  showToast(`Loaded Google Sheet settings for ${client ? client.name : 'client'}.`, 'info');
}

function selectClientAndSwitch(clientId) {
  const select = document.getElementById('global-client-select');
  if (select) {
    select.value = clientId;
    currentClientId = clientId;
    const foundClient = clientsList.find(c => c.id === currentClientId);
    if (foundClient && foundClient.currency) {
      currentCurrency = foundClient.currency;
      const currSelect = document.getElementById('global-currency-select');
      if (currSelect) currSelect.value = currentCurrency;
      localStorage.setItem('tgm_currency', currentCurrency);
    }
  }
  document.getElementById('btn-tab-dashboard').click();
  loadDashboardData();
}

async function handleDeleteClient(clientId) {
  if (!confirm('Are you sure you want to delete this agency client and its cached data?')) return;
  try {
    await api(`/api/clients/${clientId}`, { method: 'DELETE' });
    showToast('Client deleted successfully', 'success');
    loadClients();
    loadDashboardData();
  } catch (err) {
    // handled by api()
  }
}

let currentTimeframe = 'day';
let currentNomenclatureDim = 'category';
let currentStartDate = null;
let currentEndDate = null;
let currentPreset = 'all';

function formatYMD(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function setDatePreset(presetKey) {
  currentPreset = presetKey;
  const now = new Date();
  
  // Highlight active preset button
  document.querySelectorAll('.btn-preset-date').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-preset') === presetKey);
  });

  const startInput = document.getElementById('filter-start-date');
  const endInput = document.getElementById('filter-end-date');

  if (presetKey === 'today') {
    currentStartDate = formatYMD(now);
    currentEndDate = formatYMD(now);
  } else if (presetKey === 'yesterday') {
    const yest = new Date(now);
    yest.setDate(now.getDate() - 1);
    currentStartDate = formatYMD(yest);
    currentEndDate = formatYMD(yest);
  } else if (presetKey === 'this_week') {
    // Current week from Monday to Today
    const day = now.getDay();
    const diff = (day + 6) % 7; // days since Monday
    const monday = new Date(now);
    monday.setDate(now.getDate() - diff);
    currentStartDate = formatYMD(monday);
    currentEndDate = formatYMD(now);
  } else if (presetKey === 'this_month') {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    currentStartDate = formatYMD(firstDay);
    currentEndDate = formatYMD(now);
  } else if (presetKey === 'this_quarter') {
    const qStartMonth = Math.floor(now.getMonth() / 3) * 3;
    const firstQuarterDay = new Date(now.getFullYear(), qStartMonth, 1);
    currentStartDate = formatYMD(firstQuarterDay);
    currentEndDate = formatYMD(now);
  } else if (presetKey === 'last_30') {
    const l30 = new Date(now);
    l30.setDate(now.getDate() - 29);
    currentStartDate = formatYMD(l30);
    currentEndDate = formatYMD(now);
  } else if (presetKey === 'all') {
    currentStartDate = null;
    currentEndDate = null;
  }

  if (startInput) startInput.value = currentStartDate || '';
  if (endInput) endInput.value = currentEndDate || '';

  updateDateBadge();
  loadDashboardData();
}

function updateDateBadge() {
  const badge = document.getElementById('active-date-badge');
  if (!badge) return;

  const PRESET_LABELS = {
    'today': 'Today',
    'yesterday': 'Yesterday',
    'this_week': 'This Week',
    'this_month': 'This Month',
    'this_quarter': 'This Quarter',
    'last_30': 'Last 30 Days',
    'all': 'All Time (Lifetime)'
  };

  if (currentPreset in PRESET_LABELS && currentPreset !== 'custom') {
    const label = PRESET_LABELS[currentPreset];
    const dateDetail = currentStartDate 
      ? (currentStartDate === currentEndDate ? ` (${currentStartDate})` : ` (${currentStartDate} &rarr; ${currentEndDate})`) 
      : '';
    badge.innerHTML = `<span class="badge-dot active"></span> Scope: <strong>${label}</strong>${dateDetail}`;
  } else if (!currentStartDate && !currentEndDate) {
    badge.innerHTML = `<span class="badge-dot active"></span> Scope: <strong>All Time (Lifetime)</strong>`;
  } else if (currentStartDate === currentEndDate) {
    badge.innerHTML = `<span class="badge-dot active"></span> Single Day: <strong>${currentStartDate}</strong>`;
  } else {
    badge.innerHTML = `<span class="badge-dot active"></span> Custom Range: <strong>${currentStartDate || 'Min'}</strong> &rarr; <strong>${currentEndDate || 'Max'}</strong>`;
  }
}

function applyCustomDateRange() {
  const startInput = document.getElementById('filter-start-date');
  const endInput = document.getElementById('filter-end-date');
  
  const s = startInput ? startInput.value.trim() : '';
  const e = endInput ? endInput.value.trim() : '';
  
  if (s && e && s > e) {
    showToast('Start date cannot be after end date', 'error');
    return;
  }

  currentStartDate = s || null;
  currentEndDate = e || null;
  currentPreset = 'custom';

  document.querySelectorAll('.btn-preset-date').forEach(btn => btn.classList.remove('active'));
  updateDateBadge();
  loadDashboardData();
}

function setupDateFilterListeners() {
  // Preset buttons
  document.querySelectorAll('.btn-preset-date').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-preset');
      setDatePreset(preset);
    });
  });

  // Apply custom dates
  const applyBtn = document.getElementById('btn-apply-dates');
  if (applyBtn) {
    applyBtn.addEventListener('click', applyCustomDateRange);
  }

  // Reset dates
  const resetBtn = document.getElementById('btn-reset-dates');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      setDatePreset('all');
    });
  }

  // Auto-apply on change
  ['filter-start-date', 'filter-end-date'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        const s = document.getElementById('filter-start-date')?.value;
        const e = document.getElementById('filter-end-date')?.value;
        if (s && e) {
          applyCustomDateRange();
        }
      });
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyCustomDateRange();
      });
    }
  });
}

// Load Executive Dashboard
async function loadDashboardData() {
  try {
    const params = new URLSearchParams();
    if (currentClientId) params.append('client_id', currentClientId);
    params.append('timeframe', currentTimeframe);
    if (currentStartDate) params.append('start_date', currentStartDate);
    if (currentEndDate) params.append('end_date', currentEndDate);

    const summary = await api(`/api/data/summary?${params.toString()}`);
    const totals = summary.totals || {};

    // Update KPI Scorecards - Tier 1
    const totalImprEl = document.getElementById('kpi-total-impressions');
    if (totalImprEl) totalImprEl.textContent = formatNumber(totals.total_impressions || 0);

    const totalReachEl = document.getElementById('kpi-total-reach');
    if (totalReachEl) totalReachEl.textContent = formatNumber(totals.total_reach || 0);

    const freqChip = document.getElementById('kpi-frequency-chip');
    if (freqChip) freqChip.textContent = `Freq: ${(totals.frequency || 1.0).toFixed(2)}`;

    document.getElementById('kpi-total-spend').textContent = formatCurrency(totals.total_spend);
    document.getElementById('kpi-total-revenue').textContent = formatCurrency(totals.total_conversion_value);
    document.getElementById('kpi-blended-roas').textContent = (totals.purchase_roas || 0).toFixed(2) + 'x';
    document.getElementById('kpi-cost-per-purchase').textContent = formatCurrency(totals.cost_per_purchase);
    document.getElementById('kpi-purchases-count').textContent = `Purchases: ${formatNumber(totals.total_purchases)}`;
    document.getElementById('kpi-avg-purchase-value').textContent = formatCurrency(totals.avg_purchase_conversion_value);

    // Update KPI Scorecards - Tier 2 (Funnel & Rates)
    document.getElementById('kpi-total-lpv').textContent = formatNumber(totals.total_lpv);
    document.getElementById('kpi-lpv-rate').textContent = `LPV Rate: ${(totals.lpv_rate_per_link_clicks || 0).toFixed(1)}%`;
    document.getElementById('kpi-cost-per-lpv').textContent = formatCurrency(totals.cost_per_lpv);
    document.getElementById('kpi-purchase-rate-lpv').textContent = (totals.purchase_rate_per_lpv || 0).toFixed(2) + '%';
    document.getElementById('kpi-atc-pct').textContent = (totals.add_to_cart_pct || 0).toFixed(2) + '%';
    document.getElementById('kpi-cost-per-atc').textContent = `Cost/ATC: ${formatCurrency(totals.cost_per_add_to_cart)}`;
    document.getElementById('kpi-checkout-pct').textContent = (totals.checkout_initiated_pct || 0).toFixed(2) + '%';
    document.getElementById('kpi-cost-per-checkout').textContent = `Cost/IC: ${formatCurrency(totals.cost_per_checkout_initiated)}`;
    document.getElementById('kpi-video-3s-rate').textContent = (totals.video_plays_3s_rate_per_impressions || 0).toFixed(2) + '%';
    document.getElementById('kpi-cost-per-3s').textContent = `Thumbstop \u2022 Cost: ${formatCurrency(totals.cost_per_video_play_3s || 0)}`;

    // Render Charts
    const trendData = summary.time_trend || summary.daily_trend || [];
    if (trendData.length > 0) {
      initDailyTrendChart(trendData, getCurrencySymbol(currentCurrency));
    }
    if (summary.by_platform && summary.by_platform.length > 0) {
      initPlatformShareChart(summary.by_platform, getCurrencySymbol(currentCurrency));
    }

    // Populate Platform Matrix
    renderPlatformMatrix(summary.by_platform || []);

    // Load Weekly Nomenclature Table
    loadWeeklyNomenclatureData();
  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

const PLATFORM_BRAND_ICONS = {
  meta: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z"/></svg>`,
  google: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>`,
  linkedin: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.63 1.63 0 1 0 0-3.26 1.63 1.63 0 0 0 0 3.26m1.4 9.74v-8.37H5.06v8.37h2.8z"/></svg>`,
  tiktok: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.99v9.11c-.04 2.12-.8 4.24-2.27 5.75-1.74 1.83-4.32 2.72-6.84 2.37-2.48-.32-4.76-1.87-6-4.11-1.35-2.38-1.39-5.4-.1-7.81 1.25-2.39 3.65-4.04 6.33-4.34.6-.08 1.2-.09 1.8-.03v4.14c-.65-.13-1.34-.1-1.97.08-1.24.36-2.26 1.38-2.65 2.62-.43 1.35-.11 2.89.83 3.92.93 1.06 2.44 1.54 3.82 1.22 1.29-.28 2.36-1.35 2.66-2.63.15-.62.19-1.26.19-1.89V.02z"/></svg>`,
  snapchat: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12.01 2.5c-3.1 0-5.74 2.1-5.74 5.3 0 .7.1 1.4.3 2-.9.2-1.6.8-1.6 1.7 0 .6.3 1.2.8 1.5-.1.3-.2.7-.2 1.1 0 1.2.9 2.2 2.1 2.3.4.8 1.1 1.4 2 1.7-.5.3-1.3.6-2.3.8-.4.1-.7.4-.7.8 0 .5.4.9.9.9h.4c1.8-.2 3.3-.8 4.3-1.6 1 .8 2.5 1.4 4.3 1.6h.4c.5 0 .9-.4.9-.9 0-.4-.3-.7-.7-.8-1-.2-1.8-.5-2.3-.8.9-.3 1.6-.9 2-1.7 1.2-.1 2.1-1.1 2.1-2.3 0-.4-.1-.8-.2-1.1.5-.3.8-.9.8-1.5 0-.9-.7-1.5-1.6-1.7.2-.6.3-1.3.3-2 0-3.2-2.64-5.3-5.74-5.3z"/></svg>`
};

function renderPlatformMatrix(platformRows) {
  const tbody = document.getElementById('platform-matrix-body');
  if (!tbody) return;

  if (platformRows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">No platform data available for the active scope. Trigger a sync above.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  platformRows.forEach(row => {
    const tr = document.createElement('tr');
    const platKey = (row.platform || '').toLowerCase();
    const iconSvg = PLATFORM_BRAND_ICONS[platKey] || '';
    
    const roasVal = row.purchase_roas || row.roas || 0;
    let roasBadge = 'tier-low';
    if (roasVal >= 3.0) roasBadge = 'tier-high';
    else if (roasVal >= 2.0) roasBadge = 'tier-mid';

    tr.innerHTML = `
      <td>
        <span class="platform-pill ${platKey}">
          ${iconSvg}
          ${row.platform}
        </span>
      </td>
      <td style="font-weight: 700; color: #ffffff;">${formatCurrency(row.spend)}</td>
      <td>${formatNumber(row.impressions)}</td>
      <td>${formatNumber(row.link_clicks || row.clicks)}</td>
      <td>${(row.ctr || 0).toFixed(2)}%</td>
      <td>${formatCurrency(row.cpc)}</td>
      <td style="font-weight: 600;">${formatNumber(row.purchases || row.conversions)}</td>
      <td style="font-weight: 700; color: var(--accent-emerald-light);">${formatCurrency(row.conversion_value)}</td>
      <td>
        <span class="badge-roas ${roasBadge}">
          ${roasVal.toFixed(2)}x
        </span>
      </td>
      <td style="font-weight: 600;">${formatCurrency(row.cpa)}</td>
    `;
    tbody.appendChild(tr);
  });
}

let cachedNomenclatureRows = [];

// Load Weekly Nomenclature Breakdown
async function loadWeeklyNomenclatureData() {
  const tbody = document.getElementById('nomen-table-body');
  if (!tbody) return;

  try {
    const params = new URLSearchParams();
    params.append('dimension', currentNomenclatureDim);
    if (currentClientId) params.append('client_id', currentClientId);
    if (currentStartDate) params.append('start_date', currentStartDate);
    if (currentEndDate) params.append('end_date', currentEndDate);

    const rows = await api(`/api/data/nomenclature/weekly?${params.toString()}`);
    cachedNomenclatureRows = rows || [];
    renderNomenclatureRows(cachedNomenclatureRows);
  } catch (err) {
    console.error('Error loading nomenclature table:', err);
  }
}

function renderNomenclatureRows(rows) {
  const tbody = document.getElementById('nomen-table-body');
  if (!tbody) return;

  const searchInput = document.getElementById('nomen-search-input');
  const term = (searchInput ? searchInput.value : '').toLowerCase().trim();

  const filtered = term 
    ? rows.filter(r => (r.nomenclature_value || '').toLowerCase().includes(term) || (r.week_period || '').toLowerCase().includes(term))
    : rows;

  if (!filtered || filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">No taxonomy records match this filter.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  filtered.forEach(r => {
    const tr = document.createElement('tr');
    const roasVal = r.purchase_roas || 0;
    let roasBadge = 'tier-low';
    if (roasVal >= 3.0) roasBadge = 'tier-high';
    else if (roasVal >= 2.0) roasBadge = 'tier-mid';

    const purLpv = r.purchase_rate_per_lpv || 0;
    const atcPct = r.add_to_cart_pct || 0;
    const icPct = r.checkout_initiated_pct || 0;

    tr.innerHTML = `
      <td style="font-family: var(--font-mono); font-weight: 600; color: var(--text-muted); font-size: 0.76rem;">${r.week_period || 'Weekly'}</td>
      <td style="font-weight: 700; color: #ffffff; letter-spacing: -0.01em;">${r.nomenclature_value || 'Default'}</td>
      <td style="font-weight: 700;">${formatCurrency(r.spend)}</td>
      <td style="font-weight: 700; color: var(--accent-emerald-light);">${formatCurrency(r.purchases_conversion_value)}</td>
      <td style="font-weight: 600;">${formatNumber(r.purchases)}</td>
      <td>
        <span class="badge-roas ${roasBadge}">
          ${roasVal.toFixed(2)}x
        </span>
      </td>
      <td style="font-weight: 600;">${formatCurrency(r.cost_per_purchase)}</td>
      <td>${formatCurrency(r.avg_purchase_conversion_value)}</td>
      <td>${formatNumber(r.landing_page_views)}</td>
      <td>
        <div class="rate-cell">
          <span>${purLpv.toFixed(2)}%</span>
          <div class="rate-micro-bar"><div class="rate-micro-fill" style="width: ${Math.min(100, purLpv * 15)}%; background: var(--accent-violet);"></div></div>
        </div>
      </td>
      <td>
        <div class="rate-cell">
          <span>${atcPct.toFixed(2)}%</span>
          <div class="rate-micro-bar"><div class="rate-micro-fill" style="width: ${Math.min(100, atcPct * 6)}%; background: var(--accent-gold);"></div></div>
        </div>
      </td>
      <td>
        <div class="rate-cell">
          <span>${icPct.toFixed(2)}%</span>
          <div class="rate-micro-bar"><div class="rate-micro-fill" style="width: ${Math.min(100, icPct * 12)}%; background: var(--tgm-crimson);"></div></div>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Load Cleaned Records in Data Lake Tab
async function loadCleanedRecords() {
  try {
    const platform = document.getElementById('filter-platform')?.value || '';
    const search = document.getElementById('filter-search')?.value || '';

    const params = new URLSearchParams();
    if (currentClientId) params.append('client_id', currentClientId);
    if (platform) params.append('platform', platform);
    if (currentStartDate) params.append('start_date', currentStartDate);
    if (currentEndDate) params.append('end_date', currentEndDate);
    params.append('limit', '100');

    const data = await api(`/api/data/records?${params.toString()}`);
    const records = data.records || [];

    const countInfo = document.getElementById('records-count-info');
    if (countInfo) {
      countInfo.textContent = `Showing ${records.length} of ${data.total} normalized records`;
    }

    const tbody = document.getElementById('cleaned-records-body');
    if (!tbody) return;

    if (records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="12" style="text-align: center; padding: 2rem;">No records found.</td></tr>';
      return;
    }

    // Client-side search filtering
    const filtered = search
      ? records.filter(r => (r.campaign_name || '').toLowerCase().includes(search.toLowerCase()) || (r.ad_name || '').toLowerCase().includes(search.toLowerCase()))
      : records;

    tbody.innerHTML = '';
    filtered.forEach(r => {
      const tr = document.createElement('tr');
      const pClass = (r.platform || '').toLowerCase();
      tr.innerHTML = `
        <td>${r.date}</td>
        <td>${r.client_name}</td>
        <td><span class="platform-pill ${pClass}" style="font-size: 0.7rem;">${r.platform}</span></td>
        <td style="font-weight: 600; color: #fff;">${r.campaign_name}</td>
        <td style="font-weight: 700;">${formatCurrency(r.spend)}</td>
        <td>${formatNumber(r.impressions)}</td>
        <td>${formatNumber(r.clicks)}</td>
        <td>${(r.ctr || 0).toFixed(2)}%</td>
        <td>${formatCurrency(r.cpc)}</td>
        <td style="color: var(--accent-cyan); font-weight: 700;">${(r.roas || 0).toFixed(2)}x</td>
        <td style="color: var(--accent-emerald); font-weight: 700;">${formatCurrency(r.conversion_value)}</td>
        <td><span class="status-dot active" title="Cleaned & Normalized"></span> Cleaned</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading records:', err);
  }
}

// Handle Sync Execution
async function handleExecuteSync() {
  const startBtn = document.getElementById('btn-start-sync');
  startBtn.disabled = true;
  startBtn.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
    Syncing & Cleaning...
  `;

  const startDate = document.getElementById('sync-start-date').value;
  const endDate = document.getElementById('sync-end-date').value;
  const useMock = document.getElementById('sync-use-mock').checked;
  const pushBq = document.getElementById('sync-push-bq').checked;

  const selectedPlatforms = Array.from(document.querySelectorAll('.sync-platform-cb:checked')).map(cb => cb.value);

  try {
    const payload = {
      client_ids: currentClientId ? [currentClientId] : [],
      platforms: selectedPlatforms,
      start_date: startDate,
      end_date: endDate,
      use_mock: useMock,
      push_to_bigquery: pushBq
    };

    const result = await api('/api/sync/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    closeModal('modal-sync');
    showToast(`Successfully extracted ${result.rows_extracted} & cleaned ${result.rows_cleaned} records!`, 'success');

    if (result.bigquery_export && result.bigquery_export.success) {
      showToast(`Exported ${result.bigquery_export.rows_inserted} rows to BigQuery!`, 'info');
    }

    loadDashboardData();
    loadCleanedRecords();
  } catch (err) {
    // handled in api()
  } finally {
    startBtn.disabled = false;
    startBtn.innerHTML = 'Start Pipeline Execution';
  }
}

// Test Connector
async function testConnector(platform) {
  showToast(`Testing ${platform.toUpperCase()} connection...`, 'info');
  let credentials = {};

  if (platform === 'meta') {
    credentials = {
      ad_account_id: document.getElementById('meta-account-id').value,
      access_token: document.getElementById('meta-access-token').value
    };
  } else if (platform === 'google') {
    credentials = {
      customer_id: document.getElementById('google-customer-id').value,
      developer_token: document.getElementById('google-dev-token').value,
      refresh_token: document.getElementById('google-refresh-token').value
    };
  } else if (platform === 'linkedin') {
    credentials = {
      ad_account_id: document.getElementById('linkedin-account-id').value,
      access_token: document.getElementById('linkedin-access-token').value
    };
  } else if (platform === 'tiktok') {
    credentials = {
      advertiser_id: document.getElementById('tiktok-advertiser-id').value,
      access_token: document.getElementById('tiktok-access-token').value
    };
  } else if (platform === 'snapchat') {
    credentials = {
      ad_account_id: document.getElementById('snapchat-account-id').value,
      access_token: document.getElementById('snapchat-access-token').value
    };
  }

  try {
    const res = await api('/api/connectors/test', {
      method: 'POST',
      body: JSON.stringify({ platform, credentials })
    });

    if (res.success) {
      showToast(`Verified! Connected to ${res.account_name || platform} (${res.currency || 'USD'})`, 'success');
    } else {
      showToast(`Failed: ${res.error}`, 'error');
    }
  } catch (err) {
    // Handled
  }
}

// Relative Time Formatter
function formatRelativeTime(isoStr) {
  if (!isoStr) return 'Never';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// Client Selector Change in Ad Connectors Tab
function onSheetsSyncClientChanged() {
  const sheetClientSelect = document.getElementById('sheets-sync-client');
  if (!sheetClientSelect) return;
  const clientId = sheetClientSelect.value;
  const client = clientsList.find(c => c.id === clientId);
  const urlInput = document.getElementById('sheets-sync-url');
  const gidInput = document.getElementById('sheets-sync-gid');
  const statusEl = document.getElementById('sheets-sync-client-status');

  if (!client) {
    if (statusEl) statusEl.innerHTML = `<span>Select a client above.</span>`;
    return;
  }

  if (urlInput) urlInput.value = client.google_sheet_url || '';
  if (gidInput) gidInput.value = client.google_sheet_gid || '0';

  if (statusEl) {
    if (client.google_sheet_url) {
      statusEl.innerHTML = `
        <span style="color: var(--accent-emerald-light); font-weight: 700;">🟢 Sheet Configured for ${client.name}</span>
        <span>&bull;</span>
        <a href="${client.google_sheet_url}" target="_blank" style="color: var(--accent-cyan); text-decoration: none; font-weight: 600;">
          Open in Google Sheets ↗
        </a>
        ${client.last_sheet_synced_at ? `<span style="color: var(--text-dim);">(${formatRelativeTime(client.last_sheet_synced_at)})</span>` : ''}
      `;
    } else {
      statusEl.innerHTML = `
        <span style="color: #fbbf24; font-weight: 600;">⚠️ No sheet linked to ${client.name} yet.</span>
        <span>Enter the Google Sheet URL above and click Sync to save and ingest it.</span>
      `;
    }
  }
}
window.onSheetsSyncClientChanged = onSheetsSyncClientChanged;

// Trigger Google Sheets Sync (Option 1)
async function triggerGoogleSheetSync() {
  const urlInput = document.getElementById('sheets-sync-url');
  const gidInput = document.getElementById('sheets-sync-gid');
  const clientSelect = document.getElementById('sheets-sync-client');
  const replaceCb = document.getElementById('sheets-sync-replace');
  const resultCard = document.getElementById('sheets-sync-result-card');
  const btn = document.getElementById('btn-sync-google-sheet');

  const sheetUrl = urlInput ? urlInput.value.trim() : '';
  const gid = gidInput ? gidInput.value.trim() : '0';
  const clientId = clientSelect ? clientSelect.value : '';
  const replaceExisting = replaceCb ? replaceCb.checked : true;

  if (!clientId) {
    showToast('Please select a target client first', 'error');
    return;
  }

  const client = clientsList.find(c => c.id === clientId);
  const clientName = client ? client.name : 'Client';

  if (!sheetUrl && (!client || !client.google_sheet_url)) {
    showToast(`Please provide a Google Sheet URL or ID for ${clientName}`, 'error');
    return;
  }

  const origText = btn ? btn.innerHTML : 'Sync Sheet for Client';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Ingesting ${clientName}...`;
  }
  showToast(`Connecting to ${clientName}'s Google Sheet...`, 'info');

  try {
    const res = await api('/api/sheets/sync', {
      method: 'POST',
      body: JSON.stringify({
        sheet_url_or_id: sheetUrl || undefined,
        client_id: clientId,
        gid: gid || '0',
        replace_existing: replaceExisting,
        push_to_bigquery: false
      })
    });

    if (res.success) {
      showToast(`Success! Ingested & cleaned ${res.rows_imported} records for ${res.client_name}.`, 'success');
      if (resultCard) {
        resultCard.style.display = 'block';
        resultCard.style.background = 'rgba(16, 185, 129, 0.12)';
        resultCard.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        resultCard.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
            <div>
              <strong style="color: #10B981;">&#10004; Isolated Sheet Ingestion Complete for ${res.client_name}:</strong>
              <span>${res.rows_imported} records cleaned & normalized into 11 inputs and 17 metrics. (Zero overlap)</span>
            </div>
            <div style="display: flex; gap: 1rem; font-size: 0.82rem; flex-wrap: wrap;">
              <span>Spend: <strong>${formatCurrency(res.total_spend)}</strong></span>
              <span>Revenue: <strong>${formatCurrency(res.total_revenue)}</strong></span>
              <span>ROAS: <strong style="color: #FFCD57;">${res.overall_roas}x</strong></span>
              <span>Quality Score: <strong style="color: #10B981;">${res.quality_score}%</strong></span>
            </div>
          </div>
        `;
      }
      await loadClients();
      if (currentClientId === clientId || !currentClientId) {
        loadDashboardData();
        loadCleanedRecords();
      }
    }
  } catch (err) {
    if (resultCard) {
      resultCard.style.display = 'block';
      resultCard.style.background = 'rgba(218, 13, 10, 0.15)';
      resultCard.style.borderColor = 'rgba(218, 13, 10, 0.4)';
      resultCard.innerHTML = `<span style="color: #FF4D6D;">&#10006; Sync Error for ${clientName}: ${err.message}</span>`;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}
window.triggerGoogleSheetSync = triggerGoogleSheetSync;

// Direct One-Click Sync from Client Card
async function syncClientSheetDirectly(clientId, btnEl) {
  const client = clientsList.find(c => c.id === clientId);
  if (!client) return;

  if (!client.google_sheet_url) {
    openEditClientModal(clientId);
    showToast(`Please enter the Google Sheet URL for ${client.name}`, 'info');
    return;
  }

  const origHtml = btnEl ? btnEl.innerHTML : 'Sync Sheet';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = `<span class="spinner" style="width: 12px; height: 12px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Syncing...`;
  }
  showToast(`Syncing ${client.name}'s sheet...`, 'info');

  try {
    const res = await api(`/api/clients/${clientId}/sync-sheet`, { method: 'POST' });
    showToast(`✓ Synced ${res.rows_imported} records for ${client.name}!`, 'success');
    await loadClients();
    if (currentClientId === clientId || !currentClientId) {
      loadDashboardData();
      loadCleanedRecords();
    }
  } catch (err) {
    showToast(`Sync failed: ${err.message}`, 'error');
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = origHtml;
    }
  }
}
window.syncClientSheetDirectly = syncClientSheetDirectly;

// Open Edit Client & Sheet Modal
function openEditClientModal(clientId) {
  const client = clientsList.find(c => c.id === clientId);
  if (!client) return;

  document.getElementById('edit-client-id').value = client.id;
  document.getElementById('edit-client-name').value = client.name;
  document.getElementById('edit-client-website').value = client.website || '';
  document.getElementById('edit-client-currency').value = client.currency || 'INR';
  document.getElementById('edit-client-sheet-url').value = client.google_sheet_url || '';
  document.getElementById('edit-client-sheet-gid').value = client.google_sheet_gid || '0';
  document.getElementById('edit-client-modal-title').textContent = `Configure ${client.name}`;
  document.getElementById('edit-client-modal-subtitle').textContent = `Client ID: ${client.id} • Currency: ${client.currency}`;

  const linkEl = document.getElementById('edit-client-sheet-link');
  if (linkEl) {
    if (client.google_sheet_url) {
      linkEl.href = client.google_sheet_url;
      linkEl.style.display = 'inline-block';
    } else {
      linkEl.style.display = 'none';
    }
  }

  const syncTimeEl = document.getElementById('edit-client-last-synced');
  if (syncTimeEl) {
    syncTimeEl.textContent = client.last_sheet_synced_at
      ? `Last synced: ${formatRelativeTime(client.last_sheet_synced_at)}`
      : 'Last synced: Never';
  }

  // Clear data button
  const clearBtn = document.getElementById('btn-clear-client-data');
  if (clearBtn) {
    clearBtn.onclick = async () => {
      if (!confirm(`Are you sure you want to wipe all records for "${client.name}"? This removes any overlapping data so you can cleanly resync.`)) return;
      try {
        clearBtn.disabled = true;
        clearBtn.textContent = 'Wiping...';
        const res = await api(`/api/clients/${clientId}/clear-data`, { method: 'POST' });
        showToast(res.message, 'success');
        await loadClients();
        loadDashboardData();
        loadCleanedRecords();
        closeModal('modal-client-sheet');
      } catch (err) {
        showToast(`Failed to clear data: ${err.message}`, 'error');
      } finally {
        clearBtn.disabled = false;
        clearBtn.textContent = 'Wipe Overlapped Records';
      }
    };
  }

  // Save configuration only
  const saveBtn = document.getElementById('btn-save-client-sheet-only');
  if (saveBtn) {
    saveBtn.onclick = async () => {
      await saveClientSheetConfig(clientId, false);
    };
  }

  // Save and sync immediately
  const saveSyncBtn = document.getElementById('btn-save-and-sync-client-sheet');
  if (saveSyncBtn) {
    saveSyncBtn.onclick = async () => {
      await saveClientSheetConfig(clientId, true);
    };
  }

  openModal('modal-client-sheet');
}
window.openEditClientModal = openEditClientModal;

async function saveClientSheetConfig(clientId, andSync = false) {
  const name = document.getElementById('edit-client-name').value.trim();
  const website = document.getElementById('edit-client-website').value.trim();
  const currency = document.getElementById('edit-client-currency').value;
  const sheetUrl = document.getElementById('edit-client-sheet-url').value.trim();
  const sheetGid = document.getElementById('edit-client-sheet-gid').value.trim() || '0';

  if (!name) {
    showToast('Client name cannot be empty', 'error');
    return;
  }

  try {
    const client = clientsList.find(c => c.id === clientId);
    const updatedClient = {
      ...client,
      name,
      website,
      currency,
      google_sheet_url: sheetUrl,
      google_sheet_gid: sheetGid
    };

    await api(`/api/clients/${clientId}`, {
      method: 'PUT',
      body: JSON.stringify(updatedClient)
    });

    showToast(`Saved configuration for ${name}!`, 'success');
    closeModal('modal-client-sheet');
    await loadClients();

    if (andSync && sheetUrl) {
      showToast(`Ingesting sheet data for ${name}...`, 'info');
      const res = await api(`/api/clients/${clientId}/sync-sheet`, { method: 'POST' });
      showToast(`✓ Synced ${res.rows_imported} records for ${name}!`, 'success');
      await loadClients();
      loadDashboardData();
      loadCleanedRecords();
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}
window.saveClientSheetConfig = saveClientSheetConfig;

// Load BigQuery Config
async function loadBigQueryConfig() {
  try {
    const config = await api('/api/bigquery/config');
    document.getElementById('bq-project-id').value = config.project_id || '';
    document.getElementById('bq-dataset-id').value = config.dataset_id || 'tgm_reporting';
    document.getElementById('bq-table-name').value = config.table_name || 'unified_ad_performance';
    document.getElementById('bq-location').value = config.location || 'US';
    document.getElementById('bq-sa-json').value = config.service_account_json || '';
    document.getElementById('bq-auto-push').checked = !!config.auto_push;

    const badge = document.getElementById('bq-status-badge');
    if (badge) {
      if (config.connection_status === 'connected') {
        badge.textContent = 'Connected';
        badge.style.background = 'rgba(16, 185, 129, 0.2)';
        badge.style.color = 'var(--accent-emerald)';
      } else {
        badge.textContent = 'Unconfigured';
      }
    }
  } catch (err) {
    console.error('Error loading BigQuery config:', err);
  }
}

// Save BigQuery Config
async function saveBigQueryConfig() {
  const payload = {
    project_id: document.getElementById('bq-project-id').value,
    dataset_id: document.getElementById('bq-dataset-id').value,
    table_name: document.getElementById('bq-table-name').value,
    location: document.getElementById('bq-location').value,
    service_account_json: document.getElementById('bq-sa-json').value,
    auto_push: document.getElementById('bq-auto-push').checked
  };

  try {
    await api('/api/bigquery/config', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    showToast('BigQuery settings saved successfully!', 'success');
  } catch (err) {
    // Handled
  }
}

// Test BigQuery
async function testBigQueryConnection() {
  showToast('Testing BigQuery connection & permissions...', 'info');
  try {
    const res = await api('/api/bigquery/test', { method: 'POST' });
    if (res.success) {
      showToast(res.message, 'success');
      loadBigQueryConfig();
    } else {
      showToast(`Connection failed: ${res.error}`, 'error');
    }
  } catch (err) {
    // Handled
  }
}

// Deploy BigQuery Schema
async function deployBigQuerySchema() {
  showToast('Deploying partitioned table & Looker Studio views to BigQuery...', 'info');
  try {
    const res = await api('/api/bigquery/deploy', { method: 'POST' });
    if (res.success) {
      showToast(`Deployed BigQuery Table & Looker Views to ${res.dataset}!`, 'success');
    } else {
      showToast(`Deployment failed: ${res.error}`, 'error');
    }
  } catch (err) {
    // Handled
  }
}

// Load Looker Studio Resources & Embed
async function loadLookerResources() {
  try {
    const embedData = await api('/api/looker/embed-url');
    const input = document.getElementById('looker-embed-input');
    const iframe = document.getElementById('looker-embed-iframe');
    if (input && embedData.embed_url) {
      input.value = embedData.embed_url;
      if (iframe) iframe.src = embedData.embed_url;
    }
  } catch (err) {
    console.error('Error loading Looker embed:', err);
  }
}

async function saveLookerEmbedUrl() {
  const url = document.getElementById('looker-embed-input')?.value || '';
  if (!url) return;

  try {
    await api('/api/looker/embed-url', {
      method: 'POST',
      body: JSON.stringify({ embed_url: url })
    });
    const iframe = document.getElementById('looker-embed-iframe');
    if (iframe) iframe.src = url;
    showToast('Looker Studio embed URL saved and loaded!', 'success');
  } catch (err) {
    // Handled
  }
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupSyncModal();
  setupDateFilterListeners();
  setupAuthListeners();
  setupSharePortalListeners();
  setupTeamListeners();

  // Timeframe Switcher (Day*, Week, Month)
  const tfButtons = document.querySelectorAll('.btn-tf');
  tfButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tfButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTimeframe = btn.getAttribute('data-tf');
      loadDashboardData();
    });
  });

  // Nomenclature Dimension Switcher Pills
  const nomenButtons = document.querySelectorAll('.btn-nomen');
  nomenButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      nomenButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentNomenclatureDim = btn.getAttribute('data-dim');
      loadWeeklyNomenclatureData();
    });
  });

  // Nomenclature Search Filter
  const nomenSearchInput = document.getElementById('nomen-search-input');
  if (nomenSearchInput) {
    nomenSearchInput.addEventListener('input', () => {
      renderNomenclatureRows(cachedNomenclatureRows);
    });
  }

  // Client Selector Change Handler
  const clientSelect = document.getElementById('global-client-select');
  if (clientSelect) {
    clientSelect.addEventListener('change', (e) => {
      currentClientId = e.target.value;
      const foundClient = clientsList.find(c => c.id === currentClientId);
      if (foundClient && foundClient.currency) {
        currentCurrency = foundClient.currency;
        const currSelect = document.getElementById('global-currency-select');
        if (currSelect) currSelect.value = currentCurrency;
        localStorage.setItem('tgm_currency', currentCurrency);
      }
      loadDashboardData();
      loadCleanedRecords();
    });
  }

  // Currency Selector Change Handler (INR, USD, EUR, etc.)
  const currSelect = document.getElementById('global-currency-select');
  if (currSelect) {
    currSelect.value = currentCurrency;
    currSelect.addEventListener('change', (e) => {
      currentCurrency = e.target.value;
      localStorage.setItem('tgm_currency', currentCurrency);
      showToast(`Active currency switched to ${currentCurrency} (${getCurrencySymbol(currentCurrency)})`, 'info');
      loadDashboardData();
      loadCleanedRecords();
    });
  }

  // Refresh Dashboard Button
  const refreshBtn = document.getElementById('btn-refresh-dashboard');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      showToast('Refreshing dashboard metrics...', 'info');
      loadDashboardData();
    });
  }

  // Export CSV Button
  const exportBtn = document.getElementById('btn-export-csv');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const url = `/api/data/export/csv${currentClientId ? `?client_id=${currentClientId}` : ''}`;
      window.open(url, '_blank');
    });
  }

  // BigQuery Buttons
  document.getElementById('btn-save-bq-config')?.addEventListener('click', saveBigQueryConfig);
  document.getElementById('btn-test-bq')?.addEventListener('click', testBigQueryConnection);
  document.getElementById('btn-deploy-bq')?.addEventListener('click', deployBigQuerySchema);

  // Looker Studio Embed Button
  document.getElementById('btn-save-embed-url')?.addEventListener('click', saveLookerEmbedUrl);

  // Filter Search
  document.getElementById('filter-search')?.addEventListener('input', loadCleanedRecords);
  document.getElementById('filter-platform')?.addEventListener('change', loadCleanedRecords);

  // Add Client Modal Trigger
  document.getElementById('btn-add-client-modal')?.addEventListener('click', () => {
    openModal('modal-client');
  });

  // Save New Client
  document.getElementById('btn-save-new-client')?.addEventListener('click', async () => {
    const name = document.getElementById('new-client-name').value.trim();
    const website = document.getElementById('new-client-website').value.trim();
    const industry = document.getElementById('new-client-industry').value;
    const currency = document.getElementById('new-client-currency').value;
    const sheetUrl = document.getElementById('new-client-sheet-url')?.value.trim() || '';
    const sheetGid = document.getElementById('new-client-sheet-gid')?.value.trim() || '0';

    if (!name) {
      showToast('Please enter a client business name', 'error');
      return;
    }

    const newClient = {
      id: `client_${Date.now()}`,
      name,
      website,
      industry,
      currency,
      google_sheet_url: sheetUrl,
      google_sheet_gid: sheetGid,
      is_active: true
    };

    try {
      await api('/api/clients', {
        method: 'POST',
        body: JSON.stringify(newClient)
      });
      closeModal('modal-client');
      showToast(`Client ${name} created!`, 'success');
      await loadClients();

      // If a dedicated sheet URL was provided, auto-sync it right away!
      if (sheetUrl) {
        showToast(`Auto-syncing dedicated Google Sheet for ${name}...`, 'info');
        try {
          const res = await api(`/api/clients/${newClient.id}/sync-sheet`, { method: 'POST' });
          showToast(`✓ Ingested ${res.rows_imported} records for ${name}!`, 'success');
          await loadClients();
          loadDashboardData();
        } catch (syncErr) {
          showToast(`Client saved, but initial sheet sync failed: ${syncErr.message}`, 'warning');
        }
      }
    } catch (err) {
      // Handled
    }
  });

  // Check Session Authentication and Initialize Studio
  await checkAuthAndInit();
});

// ----------------- Authentication & Access Gate Controller ----------------- //

function setupAuthListeners() {
  const form = document.getElementById('form-login');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await handleLoginSubmit();
    });
  }

  const btnSubmit = document.getElementById('btn-submit-login');
  if (btnSubmit) {
    btnSubmit.addEventListener('click', handleLoginSubmit);
  }

  // Quick Switch Admin Demo
  const btnAdmin = document.getElementById('btn-quick-admin');
  if (btnAdmin) {
    btnAdmin.addEventListener('click', () => {
      document.getElementById('login-email').value = 'admin@thinkgrowmedia.com';
      document.getElementById('login-password').value = 'admin';
      handleLoginSubmit();
    });
  }

  // Quick Switch Member Demo
  const btnMember = document.getElementById('btn-quick-member');
  if (btnMember) {
    btnMember.addEventListener('click', () => {
      document.getElementById('login-email').value = 'alex@thinkgrowmedia.com';
      document.getElementById('login-password').value = 'alex123';
      handleLoginSubmit();
    });
  }

  // Header Logout Button
  const btnLogout = document.getElementById('btn-header-logout');
  if (btnLogout) {
    btnLogout.addEventListener('click', handleLogout);
  }
}

async function handleLoginSubmit() {
  const emailInput = document.getElementById('login-email');
  const pwdInput = document.getElementById('login-password');
  const alertEl = document.getElementById('login-error-alert');
  const btn = document.getElementById('btn-submit-login');

  const email = emailInput ? emailInput.value.trim() : '';
  const password = pwdInput ? pwdInput.value : '';

  if (!email || !password) {
    if (alertEl) {
      alertEl.textContent = 'Please enter both email and password.';
      alertEl.style.display = 'block';
    }
    return;
  }

  if (alertEl) alertEl.style.display = 'none';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Verifying Credentials...';
  }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed. Please check credentials.');
    }

    localStorage.setItem('tgm_session_token', data.token);
    currentUser = data.user;
    updateHeaderUserProfile(currentUser);
    closeModal('modal-login');
    showToast(`Welcome back, ${currentUser.name}!`, 'success');

    // Reload clients and dashboard scoped to user permissions
    currentClientId = '';
    await loadClients();
    await loadDashboardData();
  } catch (err) {
    if (alertEl) {
      alertEl.textContent = err.message;
      alertEl.style.display = 'block';
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Sign In to Studio';
    }
  }
}

async function handleLogout() {
  const token = localStorage.getItem('tgm_session_token');
  if (token) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (err) {
      // Ignore network errors on logout
    }
  }

  // Clear local session & state
  localStorage.removeItem('tgm_session_token');
  currentUser = null;
  currentClientId = '';

  // Reset header user profile to logged out / guest
  updateHeaderUserProfile(null);

  // Switch back to dashboard view
  const dashTabBtn = document.getElementById('btn-tab-dashboard');
  if (dashTabBtn) dashTabBtn.click();

  // Reset login modal inputs & alerts
  const pwdInput = document.getElementById('login-password');
  if (pwdInput) pwdInput.value = '';
  const alertEl = document.getElementById('login-error-alert');
  if (alertEl) {
    alertEl.style.display = 'none';
    alertEl.textContent = '';
  }
  const btn = document.getElementById('btn-submit-login');
  if (btn) {
    btn.disabled = false;
    btn.textContent = 'Sign In to Studio';
  }

  showToast('You have been signed out.', 'info');
  openModal('modal-login');
}
window.handleLogout = handleLogout;

function updateHeaderUserProfile(user) {
  const nameEl = document.getElementById('user-display-name');
  const roleEl = document.getElementById('user-role-badge');
  const avatarEl = document.getElementById('user-role-avatar');
  const teamTabBtn = document.getElementById('btn-tab-team');
  const addClientBtn = document.getElementById('btn-add-client-modal');
  const logoutBtn = document.getElementById('btn-header-logout');

  if (!user) {
    if (nameEl) nameEl.textContent = 'Not Signed In';
    if (roleEl) {
      roleEl.textContent = 'Guest';
      roleEl.style.color = 'var(--text-muted)';
    }
    if (avatarEl) {
      avatarEl.textContent = 'TG';
      avatarEl.style.background = 'rgba(255, 255, 255, 0.15)';
    }
    if (teamTabBtn) teamTabBtn.style.display = 'none';
    if (addClientBtn) addClientBtn.style.display = 'none';
    if (logoutBtn) {
      logoutBtn.innerHTML = `
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
        <span>Sign In</span>
      `;
      logoutBtn.onclick = () => openModal('modal-login');
    }
    return;
  }

  if (logoutBtn) {
    logoutBtn.innerHTML = `
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      <span>Logout</span>
    `;
    logoutBtn.onclick = handleLogout;
  }

  if (nameEl) nameEl.textContent = user.name.split(' ')[0] || user.name;
  
  const isAdmin = user.role === 'admin';
  if (roleEl) {
    roleEl.textContent = isAdmin ? 'Super Admin' : 'Media Buyer';
    roleEl.style.color = isAdmin ? 'var(--accent-gold)' : 'var(--accent-cyan)';
  }
  if (avatarEl) {
    const initials = user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    avatarEl.textContent = initials || 'US';
    avatarEl.style.background = isAdmin
      ? 'linear-gradient(135deg, #da0d0a, #ff1a44)'
      : 'linear-gradient(135deg, #06b6d4, #6366f1)';
  }

  // Show/Hide Team tab for Admin only
  if (teamTabBtn) {
    teamTabBtn.style.display = isAdmin ? 'flex' : 'none';
    if (!isAdmin && document.getElementById('tab-team')?.classList.contains('active')) {
      document.getElementById('btn-tab-dashboard')?.click();
    }
  }

  // Hide Add Client button for non-admins
  if (addClientBtn) {
    addClientBtn.style.display = isAdmin ? 'inline-flex' : 'none';
  }
}

async function checkAuthAndInit() {
  const token = localStorage.getItem('tgm_session_token');
  if (!token) {
    updateHeaderUserProfile(null);
    openModal('modal-login');
    return;
  }
  try {
    currentUser = await api('/api/auth/me');
    updateHeaderUserProfile(currentUser);
    closeModal('modal-login');
    await loadClients();
    await loadDashboardData();
  } catch (err) {
    localStorage.removeItem('tgm_session_token');
    currentUser = null;
    updateHeaderUserProfile(null);
    openModal('modal-login');
  }
}

// ----------------- Client Real-Time Portal Share Link Controller ----------------- //

let currentShareClientId = null;
let currentShareClientName = '';

async function openSharePortalModal(clientId, clientName) {
  try {
    currentShareClientId = clientId;
    currentShareClientName = clientName;
    const res = await api(`/api/clients/${clientId}/share-link`);
    document.getElementById('share-portal-client-title').textContent = `Client: ${res.client_name}`;
    const fullUrl = `${window.location.origin}${res.share_url}`;
    const input = document.getElementById('share-portal-url-input');
    if (input) input.value = fullUrl;

    const newTabBtn = document.getElementById('btn-open-portal-newtab');
    if (newTabBtn) {
      newTabBtn.onclick = () => window.open(fullUrl, '_blank');
    }

    openModal('modal-share-portal');
  } catch (err) {
    showToast(`Failed to generate share link: ${err.message}`, 'error');
  }
}

function setupSharePortalListeners() {
  const copyBtn = document.getElementById('btn-copy-portal-link');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const input = document.getElementById('share-portal-url-input');
      if (!input || !input.value) return;
      try {
        await navigator.clipboard.writeText(input.value);
        copyBtn.innerHTML = `
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Copied!</span>
        `;
        showToast('Real-time client portal link copied to clipboard!', 'success');
        setTimeout(() => {
          copyBtn.innerHTML = `
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            <span>Copy Link</span>
          `;
        }, 2500);
      } catch (err) {
        input.select();
        document.execCommand('copy');
        showToast('Link copied to clipboard!', 'success');
      }
    });
  }

  const regenBtn = document.getElementById('btn-regenerate-portal-token');
  if (regenBtn) {
    regenBtn.addEventListener('click', async () => {
      if (!currentShareClientId) return;
      if (!confirm(`Revoke active link for ${currentShareClientName} and generate a fresh link? The previous link will immediately stop working.`)) return;
      try {
        const res = await api(`/api/clients/${currentShareClientId}/share-link/regenerate`, { method: 'POST' });
        const fullUrl = `${window.location.origin}${res.share_url}`;
        const input = document.getElementById('share-portal-url-input');
        if (input) input.value = fullUrl;
        const newTabBtn = document.getElementById('btn-open-portal-newtab');
        if (newTabBtn) {
          newTabBtn.onclick = () => window.open(fullUrl, '_blank');
        }
        showToast('Fresh live portal link generated! Old link revoked.', 'success');
      } catch (err) {
        showToast(`Regeneration failed: ${err.message}`, 'error');
      }
    });
  }
}

// ----------------- Team & RBAC Management Controller ----------------- //

let teamUsersList = [];

function setupTeamListeners() {
  const addBtn = document.getElementById('btn-open-add-user-modal');
  if (addBtn) {
    addBtn.addEventListener('click', openAddTeamUserModal);
  }

  const roleSelect = document.getElementById('team-user-role');
  if (roleSelect) {
    roleSelect.addEventListener('change', (e) => {
      const clientGroup = document.getElementById('team-user-clients-group');
      if (clientGroup) {
        clientGroup.style.display = e.target.value === 'admin' ? 'none' : 'block';
      }
    });
  }

  const saveBtn = document.getElementById('btn-save-team-user');
  if (saveBtn) {
    saveBtn.addEventListener('click', handleSaveTeamUser);
  }
}

async function loadTeamUsers() {
  if (!currentUser || currentUser.role !== 'admin') return;
  const tbody = document.getElementById('team-users-tbody');
  if (!tbody) return;

  try {
    teamUsersList = await api('/api/team/users');
    const totalEl = document.getElementById('team-stat-total');
    const adminsEl = document.getElementById('team-stat-admins');
    const membersEl = document.getElementById('team-stat-members');

    if (totalEl) totalEl.textContent = teamUsersList.length;
    if (adminsEl) adminsEl.textContent = teamUsersList.filter(u => u.role === 'admin').length;
    if (membersEl) membersEl.textContent = teamUsersList.filter(u => u.role !== 'admin').length;

    if (teamUsersList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No team members registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = teamUsersList.map(u => {
      const isAdmin = u.role === 'admin';
      const roleBadge = isAdmin
        ? `<span class="badge" style="background: rgba(218, 13, 10, 0.18); color: var(--accent-red-light); font-weight: 700; border: 1px solid rgba(218, 13, 10, 0.4);">SUPER ADMIN</span>`
        : `<span class="badge" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan-light); font-weight: 700; border: 1px solid rgba(6, 182, 212, 0.35);">MEDIA BUYER</span>`;

      let clientAccessBadges = '';
      if (isAdmin || (u.assigned_client_ids && u.assigned_client_ids.includes('*'))) {
        clientAccessBadges = `<span class="badge" style="background: rgba(255, 205, 87, 0.15); color: var(--accent-gold); font-weight: 700;">★ All Agency Clients</span>`;
      } else if (!u.assigned_client_ids || u.assigned_client_ids.length === 0) {
        clientAccessBadges = `<span style="color: var(--text-dim); font-size: 0.78rem;">No clients assigned</span>`;
      } else {
        clientAccessBadges = u.assigned_client_ids.map(cid => {
          const clientObj = clientsList.find(c => c.id === cid);
          const cname = clientObj ? clientObj.name : cid;
          return `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald-light); margin-right: 0.25rem; margin-bottom: 0.25rem;">${cname}</span>`;
        }).join('');
      }

      const isSelf = currentUser && currentUser.id === u.id;
      const deleteBtn = isSelf
        ? `<button class="btn btn-outline btn-sm" disabled style="opacity: 0.4; cursor: not-allowed;" title="Cannot delete your logged-in admin account">&#128465;</button>`
        : `<button class="btn btn-outline btn-sm" onclick="handleDeleteTeamUser('${u.id}', '${u.name.replace(/'/g, "\\'")}')" style="color: var(--tgm-crimson);" title="Delete user">&#128465;</button>`;

      return `
        <tr>
          <td>
            <div style="font-weight: 700; color: #fff;">${u.name}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${u.email}</div>
          </td>
          <td>${roleBadge}</td>
          <td><div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">${clientAccessBadges}</div></td>
          <td>
            <span class="status-pill" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">
              <span class="status-dot active"></span>
              Active
            </span>
          </td>
          <td style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-dim);">
            ${u.created_at ? u.created_at.split('T')[0] : 'N/A'}
          </td>
          <td style="text-align: right;">
            <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
              <button class="btn btn-secondary btn-sm" onclick="openEditTeamUserModal('${u.id}')">Edit Access</button>
              ${deleteBtn}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load team users:', err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--accent-flame-light);">Failed to load team roster.</td></tr>`;
  }
}

function openAddTeamUserModal() {
  document.getElementById('modal-team-user-title').textContent = 'Add Team Member';
  document.getElementById('edit-user-id').value = '';
  document.getElementById('team-user-name').value = '';
  document.getElementById('team-user-email').value = '';
  document.getElementById('team-user-email').disabled = false;
  document.getElementById('team-user-password').value = '';
  document.getElementById('team-user-pwd-hint').style.display = 'none';
  document.getElementById('team-user-role').value = 'member';
  document.getElementById('team-user-clients-group').style.display = 'block';

  renderClientCheckboxes([]);
  openModal('modal-team-user');
}

function openEditTeamUserModal(userId) {
  const user = teamUsersList.find(u => u.id === userId);
  if (!user) return;

  document.getElementById('modal-team-user-title').textContent = `Edit Access: ${user.name}`;
  document.getElementById('edit-user-id').value = user.id;
  document.getElementById('team-user-name').value = user.name;
  document.getElementById('team-user-email').value = user.email;
  document.getElementById('team-user-email').disabled = true;
  document.getElementById('team-user-password').value = '';
  document.getElementById('team-user-pwd-hint').style.display = 'block';
  document.getElementById('team-user-role').value = user.role;
  document.getElementById('team-user-clients-group').style.display = user.role === 'admin' ? 'none' : 'block';

  renderClientCheckboxes(user.assigned_client_ids || []);
  openModal('modal-team-user');
}

function renderClientCheckboxes(checkedIds = []) {
  const container = document.getElementById('team-user-client-checkboxes');
  if (!container) return;

  if (clientsList.length === 0) {
    container.innerHTML = '<span style="color: var(--text-dim); font-size: 0.8rem;">No clients registered in the system yet.</span>';
    return;
  }

  container.innerHTML = clientsList.map(c => {
    const isChecked = checkedIds.includes('*') || checkedIds.includes(c.id);
    return `
      <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; cursor: pointer; color: #fff;">
        <input type="checkbox" class="user-client-cb" value="${c.id}" ${isChecked ? 'checked' : ''}>
        <span>${c.name} <span style="color: var(--text-muted); font-size: 0.75rem;">(${c.industry} &bull; ${c.currency})</span></span>
      </label>
    `;
  }).join('');
}

async function handleSaveTeamUser() {
  const userId = document.getElementById('edit-user-id').value;
  const name = document.getElementById('team-user-name').value.trim();
  const email = document.getElementById('team-user-email').value.trim();
  const password = document.getElementById('team-user-password').value;
  const role = document.getElementById('team-user-role').value;

  if (!name || !email) {
    showToast('Name and email are required.', 'error');
    return;
  }

  // Get assigned client checkboxes
  const assigned_client_ids = [];
  if (role === 'admin') {
    assigned_client_ids.push('*');
  } else {
    document.querySelectorAll('.user-client-cb:checked').forEach(cb => {
      assigned_client_ids.push(cb.value);
    });
  }

  try {
    if (userId) {
      // Edit User
      const payload = {
        name,
        role,
        assigned_client_ids,
        ...(password ? { password } : {})
      };
      await api(`/api/team/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      showToast(`User ${name} updated successfully!`, 'success');
    } else {
      // Add User
      if (!password) {
        showToast('Password is required for new team members.', 'error');
        return;
      }
      const payload = {
        name,
        email,
        password,
        role,
        assigned_client_ids
      };
      await api('/api/team/users', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast(`Team member ${name} created!`, 'success');
    }
    closeModal('modal-team-user');
    loadTeamUsers();
  } catch (err) {
    // Handled in api()
  }
}

async function handleDeleteTeamUser(userId, userName) {
  if (!confirm(`Are you sure you want to remove internal user "${userName}"? Their access will be revoked immediately.`)) return;
  try {
    await api(`/api/team/users/${userId}`, { method: 'DELETE' });
    showToast(`User ${userName} deleted.`, 'success');
    loadTeamUsers();
  } catch (err) {
    // Handled in api()
  }
}

// Clear Synthetic Demo Records Function
async function handleClearDemoData() {
  if (!confirm("Are you sure you want to remove all synthetic demo records and keep ONLY your live Google Sheet data?")) return;
  try {
    const res = await api('/api/data/clear-demo', { method: 'POST' });
    showToast(`Removed ${res.deleted_count} demo records! Only live sheet data remains.`, 'success');
    loadDashboardData();
    loadCleanedRecords();
  } catch (err) {
    showToast(`Error clearing demo data: ${err.message}`, 'error');
  }
}


