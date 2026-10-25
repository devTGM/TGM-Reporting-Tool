// ==============================================================================
// TGM REPORTING STUDIO - LUXURY INTERACTIVE VISUALIZATIONS
// Ultra-Smooth Cubic Curves, Ambient Gradients, Glass Tooltips & High Contrast
// Fully Dynamic Currency Formatting & Adaptive Delivery Metrics
// ==============================================================================

let dailyTrendChartInstance = null;
let platformShareChartInstance = null;

const PLATFORM_COLORS = {
  Meta: '#0081fb',
  Google: '#4285f4',
  LinkedIn: '#0a66c2',
  TikTok: '#fe2c55',
  Snapchat: '#facc15'
};

function initDailyTrendChart(dailyData, currencySym = '₹') {
  const ctx = document.getElementById('chart-daily-trend');
  if (!ctx) return;

  if (dailyTrendChartInstance) {
    dailyTrendChartInstance.destroy();
  }

  const labels = dailyData.map(d => {
    const raw = d.date || d.time_bucket || '';
    return raw.length > 5 ? raw.slice(5) : raw;
  });
  const spendData = dailyData.map(d => d.spend || 0);
  const revenueData = dailyData.map(d => d.conversion_value || 0);

  const totalSpend = spendData.reduce((a, b) => a + b, 0);
  const totalRev = revenueData.reduce((a, b) => a + b, 0);
  const isDeliveryOnly = (totalSpend === 0 && totalRev === 0);

  const canvas = ctx.getContext('2d');
  
  // Luxury Multi-Stop Gradients
  const gradient1 = canvas.createLinearGradient(0, 0, 0, 320);
  gradient1.addColorStop(0, isDeliveryOnly ? 'rgba(56, 189, 248, 0.45)' : 'rgba(16, 185, 129, 0.45)');
  gradient1.addColorStop(0.5, isDeliveryOnly ? 'rgba(56, 189, 248, 0.10)' : 'rgba(16, 185, 129, 0.12)');
  gradient1.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

  const gradient2 = canvas.createLinearGradient(0, 0, 0, 320);
  gradient2.addColorStop(0, isDeliveryOnly ? 'rgba(129, 140, 248, 0.40)' : 'rgba(218, 13, 10, 0.40)');
  gradient2.addColorStop(0.5, isDeliveryOnly ? 'rgba(129, 140, 248, 0.08)' : 'rgba(218, 13, 10, 0.08)');
  gradient2.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

  const isINR = currencySym === '₹';
  const locale = isINR ? 'en-IN' : 'en-US';
  const pRadius = dailyData.length <= 2 ? 6 : 2.5;

  const dataset1 = isDeliveryOnly ? {
    label: 'Daily Impressions',
    data: dailyData.map(d => d.impressions || 0),
    borderColor: '#38bdf8',
    backgroundColor: gradient1,
    borderWidth: 2.8,
    tension: 0.4,
    fill: true,
    pointBackgroundColor: '#38bdf8',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 1.5,
    pointRadius: pRadius,
    pointHoverRadius: 7,
    pointHoverBackgroundColor: '#7dd3fc',
    pointHoverBorderColor: '#ffffff',
    pointHoverBorderWidth: 2.5
  } : {
    label: `Attributed Revenue (${currencySym})`,
    data: revenueData,
    borderColor: '#10b981',
    backgroundColor: gradient1,
    borderWidth: 2.8,
    tension: 0.4,
    fill: true,
    pointBackgroundColor: '#10b981',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 1.5,
    pointRadius: pRadius,
    pointHoverRadius: 7,
    pointHoverBackgroundColor: '#34d399',
    pointHoverBorderColor: '#ffffff',
    pointHoverBorderWidth: 2.5
  };

  const dataset2 = isDeliveryOnly ? {
    label: 'Daily Reach',
    data: dailyData.map(d => d.reach || 0),
    borderColor: '#818cf8',
    backgroundColor: gradient2,
    borderWidth: 2.2,
    borderDash: [5, 5],
    tension: 0.4,
    fill: true,
    pointBackgroundColor: '#818cf8',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 1.5,
    pointRadius: pRadius,
    pointHoverRadius: 7,
    pointHoverBackgroundColor: '#a5b4fc',
    pointHoverBorderColor: '#ffffff',
    pointHoverBorderWidth: 2.5
  } : {
    label: `Ad Spend (${currencySym})`,
    data: spendData,
    borderColor: '#da0d0a',
    backgroundColor: gradient2,
    borderWidth: 2.2,
    borderDash: [5, 5],
    tension: 0.4,
    fill: true,
    pointBackgroundColor: '#da0d0a',
    pointBorderColor: '#ffffff',
    pointBorderWidth: 1.5,
    pointRadius: pRadius,
    pointHoverRadius: 7,
    pointHoverBackgroundColor: '#ff1a44',
    pointHoverBorderColor: '#ffffff',
    pointHoverBorderWidth: 2.5
  };

  dailyTrendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [dataset1, dataset2]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 900,
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
            color: '#94a3b8',
            font: { family: 'Inter', size: 11, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 6,
            padding: 16
          }
        },
        tooltip: {
          backgroundColor: 'rgba(14, 7, 32, 0.96)',
          titleColor: '#ffffff',
          titleFont: { family: 'Outfit', size: 13, weight: 700 },
          bodyColor: '#cbd5e1',
          bodyFont: { family: 'Inter', size: 12, weight: 500 },
          borderColor: isDeliveryOnly ? 'rgba(56, 189, 248, 0.35)' : 'rgba(218, 13, 10, 0.35)',
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
              if (context.parsed.y !== null) {
                if (isDeliveryOnly) {
                  label += Number(context.parsed.y).toLocaleString();
                } else {
                  label += currencySym + Number(context.parsed.y).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
            color: 'rgba(255, 255, 255, 0.03)',
            drawBorder: false
          },
          ticks: { 
            color: '#64748b', 
            font: { family: 'Inter', size: 10, weight: 500 },
            maxRotation: 0
          }
        },
        y: {
          grid: { 
            color: 'rgba(255, 255, 255, 0.03)',
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: { family: 'JetBrains Mono', size: 10 },
            callback: function(value) {
              if (isDeliveryOnly) {
                return (value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value);
              }
              if (isINR) {
                if (value >= 10000000) return currencySym + (value / 10000000).toFixed(1) + 'Cr';
                if (value >= 100000) return currencySym + (value / 100000).toFixed(1) + 'L';
                if (value >= 1000) return currencySym + (value / 1000).toFixed(1) + 'k';
                return currencySym + value;
              }
              return currencySym + (value >= 1000 ? (value / 1000).toFixed(1) + 'k' : value);
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

  if (platformShareChartInstance) {
    platformShareChartInstance.destroy();
  }

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
          borderColor: '#0e0620',
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
            color: '#94a3b8',
            font: { family: 'Inter', size: 11, weight: 600 },
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 6,
            padding: 12
          }
        },
        tooltip: {
          backgroundColor: 'rgba(14, 7, 32, 0.96)',
          titleColor: '#ffffff',
          titleFont: { family: 'Outfit', size: 13, weight: 700 },
          bodyColor: '#cbd5e1',
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
