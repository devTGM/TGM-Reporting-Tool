// ==============================================================================
// TGM REPORTING STUDIO - LUXURY INTERACTIVE VISUALIZATIONS
// Ultra-Smooth Cubic Curves, Ambient Gradients, Glass Tooltips & High Contrast
// Fully Dynamic Currency Formatting & Adaptive Delivery Metrics
// ==============================================================================

let dailyTrendChartInstance = null;
let platformShareChartInstance = null;
let currentTrendMetric = 'spend_vs_revenue';
let currentTrendDailyData = [];
let currentTrendCurrency = '₹';
let currentTrendTargets = {};
let currentPlatformShareData = null;
let currentPlatformShareCurrency = '₹';

function getThemeChartColors() {
  const theme = document.documentElement.getAttribute('data-theme');
  const isLight = theme === 'light' || (!theme && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches);

  return {
    isLight: isLight,
    gridColor: isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.03)',
    tickColor: isLight ? '#475569' : '#64748b',
    legendColor: isLight ? '#334155' : '#94a3b8',
    tooltipBg: isLight ? 'rgba(15, 23, 42, 0.96)' : 'rgba(14, 7, 32, 0.96)',
    tooltipTitle: '#ffffff',
    tooltipBody: '#cbd5e1',
    tooltipBorder: isLight ? 'rgba(15, 23, 42, 0.25)' : 'rgba(129, 140, 248, 0.35)',
    doughnutBorder: isLight ? '#ffffff' : '#0e0620'
  };
}

function refreshChartsTheme() {
  if (dailyTrendChartInstance && currentTrendDailyData && currentTrendDailyData.length > 0) {
    initDailyTrendChart(currentTrendDailyData, currentTrendCurrency, currentTrendMetric, currentTrendTargets);
  }
  if (platformShareChartInstance && currentPlatformShareData && currentPlatformShareData.length > 0) {
    initPlatformShareChart(currentPlatformShareData, currentPlatformShareCurrency);
  }
}

const PLATFORM_COLORS = {
  Meta: '#0081fb',
  Google: '#4285f4',
  LinkedIn: '#0a66c2',
  TikTok: '#fe2c55',
  Snapchat: '#facc15'
};

const METRIC_CONFIGS = {
  spend_vs_revenue: {
    type: 'dual',
    title: 'Daily Spend vs Revenue Trend',
    color: '#818cf8'
  },
  spend: {
    label: 'Ad Spend',
    field: 'spend',
    color: '#da0d0a',
    unit: 'currency',
    title: 'Daily Ad Spend Trend'
  },
  revenue: {
    label: 'Attributed Revenue',
    field: 'revenue',
    color: '#10b981',
    unit: 'currency',
    title: 'Daily Attributed Revenue Trend'
  },
  roas: {
    label: 'Purchase ROAS',
    field: 'roas',
    color: '#ffcd57',
    unit: 'multiplier',
    title: 'Daily Purchase ROAS Trend'
  },
  cpa: {
    label: 'Cost per Purchase (CPA)',
    field: 'cpa',
    color: '#a855f7',
    unit: 'currency',
    title: 'Daily Cost per Purchase Trend'
  },
  purchases: {
    label: 'Total Purchases',
    field: 'purchases',
    color: '#ec4899',
    unit: 'count',
    title: 'Daily Purchases / Conversions Trend'
  },
  impressions: {
    label: 'Total Impressions',
    field: 'impressions',
    color: '#38bdf8',
    unit: 'count',
    title: 'Daily Impressions Trend'
  },
  reach: {
    label: 'Total Reach',
    field: 'reach',
    color: '#818cf8',
    unit: 'count',
    title: 'Daily Reach Trend'
  },
  clicks: {
    label: 'Link Clicks',
    field: 'clicks',
    color: '#34d399',
    unit: 'count',
    title: 'Daily Link Clicks Trend'
  },
  lpv: {
    label: 'Landing Page Views',
    field: 'lpv',
    color: '#06b6d4',
    unit: 'count',
    title: 'Daily Landing Page Views Trend'
  },
  cost_per_lpv: {
    label: 'Cost per LPV',
    field: 'cost_per_lpv',
    color: '#f59e0b',
    unit: 'currency',
    title: 'Daily Cost per LPV Trend'
  },
  ctr: {
    label: 'Click-Through Rate (CTR %)',
    field: 'ctr',
    color: '#6366f1',
    unit: 'percent',
    title: 'Daily CTR Trend'
  },
  cpc: {
    label: 'Cost per Click (CPC)',
    field: 'cpc',
    color: '#14b8a6',
    unit: 'currency',
    title: 'Daily CPC Trend'
  },
  cpm: {
    label: 'Cost per 1,000 Impressions (CPM)',
    field: 'cpm',
    color: '#8b5cf6',
    unit: 'currency',
    title: 'Daily CPM Trend'
  },
  atc: {
    label: 'Adds to Cart',
    field: 'atc',
    color: '#fbbf24',
    unit: 'count',
    title: 'Daily Adds to Cart Trend'
  },
  checkouts: {
    label: 'Checkouts Initiated',
    field: 'checkouts',
    color: '#f43f5e',
    unit: 'count',
    title: 'Daily Checkouts Initiated Trend'
  }
};

function initDailyTrendChart(dailyData, currencySym = '₹', metric = null, targets = null) {
  if (dailyData) currentTrendDailyData = dailyData;
  if (currencySym) currentTrendCurrency = currencySym;
  if (targets) currentTrendTargets = targets;
  if (metric) currentTrendMetric = metric;

  const activeMetric = currentTrendMetric || 'spend_vs_revenue';
  const data = currentTrendDailyData || [];
  const ctx = document.getElementById('chart-daily-trend');
  if (!ctx || data.length === 0) return;

  if (dailyTrendChartInstance) {
    dailyTrendChartInstance.destroy();
  }

  const isINR = currentTrendCurrency === '₹';
  const locale = isINR ? 'en-IN' : 'en-US';
  const pRadius = data.length <= 2 ? 6 : 2.5;

  const labels = data.map(d => {
    const raw = d.date || d.time_bucket || '';
    return raw.length > 5 ? raw.slice(5) : raw;
  });

  const canvas = ctx.getContext('2d');
  const datasets = [];
  const themeColors = getThemeChartColors();

  const cfg = METRIC_CONFIGS[activeMetric] || METRIC_CONFIGS.spend_vs_revenue;
  const titleEl = document.getElementById('daily-trend-chart-title');
  if (titleEl) {
    titleEl.innerHTML = `
      <svg width="18" height="18" fill="none" stroke="${cfg.color}" stroke-width="2" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      ${cfg.title}
    `;
  }

  if (activeMetric === 'spend_vs_revenue') {
    const spendData = data.map(d => d.spend || 0);
    const revenueData = data.map(d => d.conversion_value !== undefined ? d.conversion_value : (d.revenue || 0));
    const totalSpend = spendData.reduce((a, b) => a + b, 0);
    const totalRev = revenueData.reduce((a, b) => a + b, 0);
    const isDeliveryOnly = (totalSpend === 0 && totalRev === 0);

    const gradient1 = canvas.createLinearGradient(0, 0, 0, 320);
    gradient1.addColorStop(0, isDeliveryOnly ? 'rgba(56, 189, 248, 0.45)' : 'rgba(16, 185, 129, 0.45)');
    gradient1.addColorStop(0.5, isDeliveryOnly ? 'rgba(56, 189, 248, 0.10)' : 'rgba(16, 185, 129, 0.12)');
    gradient1.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

    const gradient2 = canvas.createLinearGradient(0, 0, 0, 320);
    gradient2.addColorStop(0, isDeliveryOnly ? 'rgba(129, 140, 248, 0.40)' : 'rgba(218, 13, 10, 0.40)');
    gradient2.addColorStop(0.5, isDeliveryOnly ? 'rgba(129, 140, 248, 0.08)' : 'rgba(218, 13, 10, 0.08)');
    gradient2.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

    datasets.push(isDeliveryOnly ? {
      label: 'Daily Impressions',
      data: data.map(d => d.impressions || 0),
      borderColor: '#38bdf8',
      backgroundColor: gradient1,
      borderWidth: 2.8,
      tension: 0.4,
      fill: true,
      pointBackgroundColor: '#38bdf8',
      pointBorderColor: '#ffffff',
      pointRadius: pRadius,
      pointHoverRadius: 7
    } : {
      label: `Attributed Revenue (${currentTrendCurrency})`,
      data: revenueData,
      borderColor: '#10b981',
      backgroundColor: gradient1,
      borderWidth: 2.8,
      tension: 0.4,
      fill: true,
      pointBackgroundColor: '#10b981',
      pointBorderColor: '#ffffff',
      pointRadius: pRadius,
      pointHoverRadius: 7
    });

    datasets.push(isDeliveryOnly ? {
      label: 'Daily Reach',
      data: data.map(d => d.reach || 0),
      borderColor: '#818cf8',
      backgroundColor: gradient2,
      borderWidth: 2.2,
      borderDash: [5, 5],
      tension: 0.4,
      fill: true,
      pointBackgroundColor: '#818cf8',
      pointBorderColor: '#ffffff',
      pointRadius: pRadius,
      pointHoverRadius: 7
    } : {
      label: `Ad Spend (${currentTrendCurrency})`,
      data: spendData,
      borderColor: '#da0d0a',
      backgroundColor: gradient2,
      borderWidth: 2.2,
      borderDash: [5, 5],
      tension: 0.4,
      fill: true,
      pointBackgroundColor: '#da0d0a',
      pointBorderColor: '#ffffff',
      pointRadius: pRadius,
      pointHoverRadius: 7
    });
  } else {
    // Single Metric Mode
    const values = data.map(d => {
      if (cfg.field === 'revenue') return d.conversion_value !== undefined ? d.conversion_value : (d.revenue || 0);
      if (cfg.field === 'roas') return d.purchase_roas !== undefined ? d.purchase_roas : (d.roas || 0);
      if (cfg.field === 'cpa') return d.cost_per_purchase !== undefined ? d.cost_per_purchase : (d.cpa || 0);
      if (cfg.field === 'clicks') return d.link_clicks !== undefined ? d.link_clicks : (d.clicks || 0);
      if (cfg.field === 'lpv') return d.landing_page_views !== undefined ? d.landing_page_views : (d.lpv || 0);
      if (cfg.field === 'atc') return d.adds_to_cart !== undefined ? d.adds_to_cart : (d.atc || 0);
      if (cfg.field === 'checkouts') return d.checkouts_initiated !== undefined ? d.checkouts_initiated : (d.checkouts || 0);
      return d[cfg.field] || 0;
    });

    const gradient = canvas.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, `${cfg.color}55`);
    gradient.addColorStop(0.5, `${cfg.color}15`);
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

    datasets.push({
      label: cfg.label,
      data: values,
      borderColor: cfg.color,
      backgroundColor: gradient,
      borderWidth: 2.8,
      tension: 0.38,
      fill: true,
      pointBackgroundColor: cfg.color,
      pointBorderColor: '#ffffff',
      pointBorderWidth: 1.5,
      pointRadius: pRadius,
      pointHoverRadius: 7,
      pointHoverBackgroundColor: cfg.color,
      pointHoverBorderColor: '#ffffff',
      pointHoverBorderWidth: 2.5
    });

    // Check if a target benchmark exists for this metric
    let targetVal = null;
    if (currentTrendTargets) {
      if (activeMetric === 'roas' && currentTrendTargets.roas) targetVal = parseFloat(currentTrendTargets.roas);
      else if (activeMetric === 'cpa' && currentTrendTargets.cpa) targetVal = parseFloat(currentTrendTargets.cpa);
      else if (activeMetric === 'spend' && currentTrendTargets.spend) targetVal = parseFloat(currentTrendTargets.spend) / 30;
      else if (activeMetric === 'revenue' && currentTrendTargets.revenue) targetVal = parseFloat(currentTrendTargets.revenue) / 30;
      else if (activeMetric === 'ctr' && currentTrendTargets.ctr) targetVal = parseFloat(currentTrendTargets.ctr);
      else if (activeMetric === 'cost_per_lpv' && currentTrendTargets.cost_per_lpv) targetVal = parseFloat(currentTrendTargets.cost_per_lpv);
    }

    if (targetVal !== null && !isNaN(targetVal) && targetVal > 0) {
      datasets.push({
        label: `Target Benchmark (${targetVal}${cfg.unit === 'multiplier' ? 'x' : cfg.unit === 'percent' ? '%' : ''})`,
        data: labels.map(() => targetVal),
        borderColor: '#ffcd57',
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false
      });
    }
  }

  dailyTrendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 750,
        easing: 'easeOutQuart'
      },
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: {
            color: themeColors.legendColor,
            font: { family: 'Inter', size: 11, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 6,
            padding: 16
          }
        },
        tooltip: {
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipTitle,
          titleFont: { family: 'Outfit', size: 13, weight: 700 },
          bodyColor: themeColors.tooltipBody,
          bodyFont: { family: 'Inter', size: 12, weight: 500 },
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          usePointStyle: true,
          boxWidth: 8,
          cornerRadius: 10,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) label += ': ';
              const y = context.parsed.y;
              if (y !== null) {
                if (cfg.unit === 'currency' || activeMetric === 'spend_vs_revenue') {
                  label += currentTrendCurrency + Number(y).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                } else if (cfg.unit === 'multiplier') {
                  label += Number(y).toFixed(2) + 'x';
                } else if (cfg.unit === 'percent') {
                  label += Number(y).toFixed(2) + '%';
                } else {
                  label += Number(y).toLocaleString();
                }
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: themeColors.gridColor,
            drawBorder: false
          },
          ticks: {
            color: themeColors.tickColor,
            font: { family: 'Inter', size: 10, weight: 500 },
            maxRotation: 0
          }
        },
        y: {
          grid: {
            color: themeColors.gridColor,
            drawBorder: false
          },
          ticks: {
            color: themeColors.tickColor,
            font: { family: 'JetBrains Mono', size: 10 },
            callback: function(value) {
              if (cfg.unit === 'multiplier') return value + 'x';
              if (cfg.unit === 'percent') return value + '%';
              if (cfg.unit === 'count') return value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value;
              if (isINR) {
                if (value >= 10000000) return currentTrendCurrency + (value / 10000000).toFixed(1) + 'Cr';
                if (value >= 100000) return currentTrendCurrency + (value / 100000).toFixed(1) + 'L';
                if (value >= 1000) return currentTrendCurrency + (value / 1000).toFixed(1) + 'k';
                return currentTrendCurrency + value;
              }
              return currentTrendCurrency + (value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value);
            }
          }
        }
      }
    }
  });
}

function initPlatformShareChart(platformData, currencySym = '₹') {
  const ctx = document.getElementById('chart-platform-share');
  if (!ctx) return;

  currentPlatformShareData = platformData;
  if (currencySym) currentPlatformShareCurrency = currencySym;

  if (platformShareChartInstance) {
    platformShareChartInstance.destroy();
  }

  const themeColors = getThemeChartColors();

  const labels = platformData.map(p => p.platform);
  const rawSpend = platformData.map(p => p.spend || 0);
  const totalSpend = rawSpend.reduce((a, b) => a + b, 0);
  
  // Adaptive: If spend is 0, plot platform share by Impressions!
  const isByImpr = (totalSpend === 0);
  const data = isByImpr ? platformData.map(p => p.impressions || 1) : rawSpend;
  const colors = labels.map(l => PLATFORM_COLORS[l] || '#6366f1');

  const isINR = currencySym === '₹';
  const locale = isINR ? 'en-IN' : 'en-US';

  platformShareChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: colors,
          borderColor: themeColors.doughnutBorder,
          borderWidth: 3,
          hoverOffset: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '74%',
      animation: {
        duration: 900,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: themeColors.legendColor,
            font: { family: 'Inter', size: 11, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 6,
            padding: 12
          }
        },
        tooltip: {
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipTitle,
          titleFont: { family: 'Outfit', size: 13, weight: 700 },
          bodyColor: themeColors.tooltipBody,
          bodyFont: { family: 'Inter', size: 12 },
          borderColor: isByImpr ? 'rgba(56, 189, 248, 0.35)' : 'rgba(218, 13, 10, 0.35)',
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          cornerRadius: 10,
          callbacks: {
            label: function(context) {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const val = context.parsed;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              if (isByImpr) {
                return ` ${context.label}: ${Number(val).toLocaleString()} Impr (${pct}%)`;
              }
              const formattedVal = Number(val).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              return ` ${context.label}: ${currencySym}${formattedVal} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}
