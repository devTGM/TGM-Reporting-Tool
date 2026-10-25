/**
 * Think Grow Media - Client Real-Time Portal Controller
 * Zero Login Required &bull; Token-Authenticated Real-time Telemetry
 */

(function () {
  'use strict';

  // State
  let currentToken = null;
  let currentClient = null;
  let currentCurrency = 'INR';
  let activePreset = 'all';
  let customStartDate = null;
  let customEndDate = null;
  let activeDimension = 'category';
  let trendChartInstance = null;

  // Currency exchange rates (base INR)
  const CURRENCY_RATES = {
    INR: { rate: 1.0, symbol: '₹', locale: 'en-IN' },
    USD: { rate: 0.012, symbol: '$', locale: 'en-US' },
    EUR: { rate: 0.011, symbol: '€', locale: 'de-DE' },
    GBP: { rate: 0.0095, symbol: '£', locale: 'en-GB' },
    AED: { rate: 0.044, symbol: 'د.إ', locale: 'ar-AE' }
  };

  function formatCurrency(amount) {
    const val = (Number(amount) || 0) * (CURRENCY_RATES[currentCurrency]?.rate || 1.0);
    const sym = CURRENCY_RATES[currentCurrency]?.symbol || '₹';
    const loc = CURRENCY_RATES[currentCurrency]?.locale || 'en-IN';
    return sym + Number(val.toFixed(2)).toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatNumber(num) {
    const loc = CURRENCY_RATES[currentCurrency]?.locale || 'en-IN';
    return Number(num || 0).toLocaleString(loc);
  }

  // Calculate Date Ranges
  function calculatePresetRange(preset) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const toYMD = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (preset === 'today') {
      const todayStr = toYMD(now);
      return { start: todayStr, end: todayStr, label: 'Viewing: Today' };
    }
    if (preset === 'yesterday') {
      const y = new Date(now);
      y.setDate(now.getDate() - 1);
      const yStr = toYMD(y);
      return { start: yStr, end: yStr, label: 'Viewing: Yesterday' };
    }
    if (preset === 'this_week') {
      const current = new Date(now);
      const day = current.getDay();
      const diffToMonday = current.getDate() - day + (day === 0 ? -6 : 1);
      const monday = new Date(current.setDate(diffToMonday));
      return { start: toYMD(monday), end: toYMD(now), label: `Viewing: This Week (${toYMD(monday)} to Today)` };
    }
    if (preset === 'this_month') {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      return { start: toYMD(firstDay), end: toYMD(now), label: `Viewing: This Month (${now.toLocaleString('default', { month: 'long', year: 'numeric' })})` };
    }
    if (preset === 'this_quarter') {
      const qMonth = Math.floor(now.getMonth() / 3) * 3;
      const qStart = new Date(now.getFullYear(), qMonth, 1);
      return { start: toYMD(qStart), end: toYMD(now), label: `Viewing: This Quarter (Q${Math.floor(now.getMonth() / 3) + 1} ${now.getFullYear()})` };
    }
    if (preset === 'last_30') {
      const past30 = new Date(now);
      past30.setDate(now.getDate() - 30);
      return { start: toYMD(past30), end: toYMD(now), label: `Viewing: Last 30 Days (${toYMD(past30)} to Today)` };
    }
    return { start: null, end: null, label: 'Viewing: All Available Historical Records' };
  }

  // Initialization
  async function init() {
    const params = new URLSearchParams(window.location.search);
    currentToken = params.get('token');

    if (!currentToken) {
      showError('No access token provided. Please use the complete share link sent by Think Grow Media.');
      return;
    }

    setupEventListeners();
    await loadPortalData();
  }

  function showError(msg) {
    document.getElementById('portal-live-view').style.display = 'none';
    const errView = document.getElementById('portal-error-view');
    errView.style.display = 'block';
    if (msg) {
      const p = errView.querySelector('p');
      if (p) p.innerText = msg;
    }
  }

  function setupEventListeners() {
    // Currency Switcher
    const currSelect = document.getElementById('portal-currency-select');
    if (currSelect) {
      currSelect.addEventListener('change', (e) => {
        currentCurrency = e.target.value;
        loadPortalData();
      });
    }

    // Refresh Button
    const btnRef = document.getElementById('btn-portal-refresh');
    if (btnRef) {
      btnRef.addEventListener('click', () => {
        loadPortalData();
      });
    }

    // Date Preset Buttons
    document.querySelectorAll('.btn-date-preset').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.btn-date-preset').forEach((b) => b.classList.remove('active'));
        e.target.classList.add('active');
        activePreset = e.target.getAttribute('data-preset');
        customStartDate = null;
        customEndDate = null;
        document.getElementById('portal-filter-start-date').value = '';
        document.getElementById('portal-filter-end-date').value = '';
        loadPortalData();
      });
    });

    // Custom Dates
    const btnApply = document.getElementById('btn-apply-portal-dates');
    if (btnApply) {
      btnApply.addEventListener('click', () => {
        const s = document.getElementById('portal-filter-start-date').value;
        const e = document.getElementById('portal-filter-end-date').value;
        if (!s || !e) {
          alert('Please select both Start and End dates.');
          return;
        }
        if (s > e) {
          alert('Start date must be before or equal to End date.');
          return;
        }
        document.querySelectorAll('.btn-date-preset').forEach((b) => b.classList.remove('active'));
        activePreset = 'custom';
        customStartDate = s;
        customEndDate = e;
        document.getElementById('portal-active-date-label').innerText = `Viewing Custom Scope: ${s} to ${e}`;
        loadPortalData();
      });
    }

    const btnClear = document.getElementById('btn-clear-portal-dates');
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        document.getElementById('portal-filter-start-date').value = '';
        document.getElementById('portal-filter-end-date').value = '';
        activePreset = 'all';
        customStartDate = null;
        customEndDate = null;
        document.querySelectorAll('.btn-date-preset').forEach((b) => b.classList.remove('active'));
        const allBtn = document.querySelector('.btn-date-preset[data-preset="all"]');
        if (allBtn) allBtn.classList.add('active');
        loadPortalData();
      });
    }

    // Dimension Toggles
    const dimToggle = document.getElementById('portal-dim-toggle');
    if (dimToggle) {
      dimToggle.querySelectorAll('.btn-tf').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          dimToggle.querySelectorAll('.btn-tf').forEach((b) => b.classList.remove('active'));
          e.target.classList.add('active');
          activeDimension = e.target.getAttribute('data-dim');
          loadNomenclatureTable();
        });
      });
    }

    // Export CSV
    const btnCsv = document.getElementById('btn-export-portal-csv');
    if (btnCsv) {
      btnCsv.addEventListener('click', () => {
        if (!currentClient) return;
        window.open(`/api/data/export/csv?client_id=${currentClient.client_id}`, '_blank');
      });
    }
  }

  async function loadPortalData() {
    let start = customStartDate;
    let end = customEndDate;

    if (activePreset !== 'custom') {
      const range = calculatePresetRange(activePreset);
      start = range.start;
      end = range.end;
      const lbl = document.getElementById('portal-active-date-label');
      if (lbl) lbl.innerText = range.label;
    }

    let url = `/api/portal/${currentToken}/summary?timeframe=day`;
    if (start) url += `&start_date=${start}`;
    if (end) url += `&end_date=${end}`;

    try {
      const res = await fetch(url);
      if (!res.ok) {
        if (res.status === 404 || res.status === 401) {
          showError('Invalid, revoked, or expired client share link.');
          return;
        }
        throw new Error('Failed to load performance telemetry');
      }

      const data = await res.json();
      currentClient = data.client;
      renderClientInfo(data.client);
      renderKPIs(data.summary?.totals || {});
      renderFunnel(data.summary?.totals || {});
      renderTrendChart(data.summary?.trends || []);
      await loadNomenclatureTable();

      const syncEl = document.getElementById('portal-sync-ts');
      if (syncEl) syncEl.innerText = new Date().toLocaleTimeString();
    } catch (err) {
      console.error('Portal load error:', err);
    }
  }

  function renderClientInfo(client) {
    if (!client) return;
    document.title = `${client.client_full_name || client.client_name} &bull; Live Client Portal &bull; Think Grow Media`;
    const nameEl = document.getElementById('portal-client-name');
    if (nameEl) nameEl.innerText = client.client_full_name || client.client_name;

    const subEl = document.getElementById('portal-client-sub');
    if (subEl) {
      subEl.innerText = `${client.industry || 'eCommerce Growth'} &bull; Base Currency: ${client.currency || 'INR'} &bull; Direct Agency Verified`;
    }
  }

  function renderKPIs(totals) {
    const spend = totals.total_spend || 0;
    const rev = totals.total_conversion_value || 0;
    const roas = totals.purchase_roas || 0;
    const purchases = totals.total_purchases || 0;
    const lpv = totals.total_lpv || 0;
    const reach = totals.total_reach || 0;
    const impr = totals.total_impressions || 0;
    const aov = totals.avg_purchase_conversion_value || 0;
    const cpa = totals.cost_per_purchase || 0;
    const cpc = totals.cpc || 0;
    const cpm = totals.cpm || 0;
    const freq = totals.frequency || 1.0;

    document.getElementById('portal-kpi-spend').innerText = formatCurrency(spend);
    document.getElementById('portal-kpi-revenue').innerText = formatCurrency(rev);
    
    const roasEl = document.getElementById('portal-kpi-roas');
    roasEl.innerText = `${roas.toFixed(2)}x`;
    if (roas >= 2.0) {
      roasEl.style.color = 'var(--accent-emerald-light)';
    } else if (roas >= 1.0) {
      roasEl.style.color = 'var(--accent-gold)';
    } else {
      roasEl.style.color = 'var(--accent-flame-light)';
    }

    document.getElementById('portal-kpi-purchases').innerText = formatNumber(purchases);
    document.getElementById('portal-kpi-lpv').innerText = formatNumber(lpv);
    document.getElementById('portal-kpi-reach').innerText = formatNumber(reach);
    document.getElementById('portal-kpi-impressions-sub').innerText = `${formatNumber(impr)} impressions &bull; Freq: ${freq.toFixed(2)}`;
    document.getElementById('portal-kpi-aov').innerText = formatCurrency(aov);
    document.getElementById('portal-kpi-cpa').innerText = formatCurrency(cpa);
    document.getElementById('portal-kpi-cpc-sub').innerText = `CPC: ${formatCurrency(cpc)} &bull; CPM: ${formatCurrency(cpm)}`;
  }

  function renderFunnel(totals) {
    const lpvRate = totals.lpv_rate_per_link_clicks || 0;
    const atcRate = totals.add_to_cart_pct || 0;
    const icRate = totals.checkout_initiated_pct || 0;
    const cvr = totals.purchase_rate_per_lpv || 0;

    document.getElementById('portal-funnel-lpv-rate').innerText = `${lpvRate.toFixed(1)}%`;
    document.getElementById('portal-bar-lpv').style.width = `${Math.min(lpvRate, 100)}%`;

    document.getElementById('portal-funnel-atc-rate').innerText = `${atcRate.toFixed(1)}%`;
    document.getElementById('portal-bar-atc').style.width = `${Math.min(atcRate * 2, 100)}%`;

    document.getElementById('portal-funnel-ic-rate').innerText = `${icRate.toFixed(1)}%`;
    document.getElementById('portal-bar-ic').style.width = `${Math.min(icRate * 2.5, 100)}%`;

    document.getElementById('portal-funnel-cvr').innerText = `${cvr.toFixed(1)}%`;
    document.getElementById('portal-bar-cvr').style.width = `${Math.min(cvr * 5, 100)}%`;
  }

  function renderTrendChart(trends) {
    const canvas = document.getElementById('portalTrendChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (trendChartInstance) {
      trendChartInstance.destroy();
    }

    const labels = trends.map((t) => t.period);
    const rate = CURRENCY_RATES[currentCurrency]?.rate || 1.0;
    const spendData = trends.map((t) => (t.spend * rate).toFixed(2));
    const revData = trends.map((t) => (t.revenue * rate).toFixed(2));

    trendChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: `Revenue (${CURRENCY_RATES[currentCurrency]?.symbol || '₹'})`,
            data: revData,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.12)',
            borderWidth: 2.5,
            tension: 0.35,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6
          },
          {
            label: `Ad Spend (${CURRENCY_RATES[currentCurrency]?.symbol || '₹'})`,
            data: spendData,
            borderColor: '#da0d0a',
            backgroundColor: 'rgba(218, 13, 10, 0.10)',
            borderWidth: 2,
            tension: 0.35,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: '#cbd5e1',
              font: { family: 'Outfit', size: 12 }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(14, 6, 32, 0.95)',
            titleColor: '#fff',
            bodyColor: '#cbd5e1',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            padding: 10
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#808b9e', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: {
              color: '#808b9e',
              font: { family: 'JetBrains Mono', size: 10 },
              callback: function (val) {
                return (CURRENCY_RATES[currentCurrency]?.symbol || '₹') + Number(val).toLocaleString();
              }
            }
          }
        }
      }
    });
  }

  async function loadNomenclatureTable() {
    let start = customStartDate;
    let end = customEndDate;
    if (activePreset !== 'custom') {
      const range = calculatePresetRange(activePreset);
      start = range.start;
      end = range.end;
    }

    let url = `/api/portal/${currentToken}/nomenclature?dimension=${activeDimension}`;
    if (start) url += `&start_date=${start}`;
    if (end) url += `&end_date=${end}`;

    const tbody = document.getElementById('portal-breakdown-body');
    if (!tbody) return;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch breakdown');
      const data = await res.json();
      const rows = data.records || [];

      if (rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">No records found for the selected scope.</td></tr>`;
        return;
      }

      tbody.innerHTML = rows
        .map((r) => {
          const roas = r.purchase_roas || 0;
          let roasBadge = `<span class="badge" style="background: rgba(255, 26, 68, 0.15); color: var(--accent-flame-light);">${roas.toFixed(2)}x</span>`;
          if (roas >= 2.0) {
            roasBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald-light); font-weight: 700;">${roas.toFixed(2)}x</span>`;
          } else if (roas >= 1.0) {
            roasBadge = `<span class="badge" style="background: rgba(255, 205, 87, 0.15); color: var(--accent-gold); font-weight: 700;">${roas.toFixed(2)}x</span>`;
          }

          return `
            <tr>
              <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">${r.week_period || 'N/A'}</td>
              <td style="font-weight: 600; color: #fff;">${r.nomenclature_value || 'Uncategorized'}</td>
              <td style="font-family: var(--font-mono); font-weight: 600;">${formatCurrency(r.spend)}</td>
              <td style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-emerald);">${formatCurrency(r.purchases_conversion_value)}</td>
              <td>${roasBadge}</td>
              <td style="font-family: var(--font-mono);">${formatNumber(r.purchases)}</td>
              <td style="font-family: var(--font-mono); font-size: 0.82rem;">${formatCurrency(r.cost_per_purchase)}</td>
              <td style="font-family: var(--font-mono); font-size: 0.82rem;">${formatNumber(r.landing_page_views)}</td>
              <td style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--accent-cyan);">${(r.ctr || 0).toFixed(2)}%</td>
              <td style="font-family: var(--font-mono); font-size: 0.82rem;">${formatCurrency(r.cpc)}</td>
            </tr>
          `;
        })
        .join('');
    } catch (err) {
      console.error('Nomenclature error:', err);
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 2rem; color: var(--accent-flame-light);">Failed to load strategy breakdown.</td></tr>`;
    }
  }

  // Run on page load
  document.addEventListener('DOMContentLoaded', init);
})();
