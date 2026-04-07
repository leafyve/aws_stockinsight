/* ════════════════════════════════════════════════
   STOCKINSIGHT — script.js
   ECharts · Autocomplete · Timeframe · Theme · UI
   ════════════════════════════════════════════════ */

// ── Chart state ──────────────────────────────
let echartsInstance = null;
let storedData = [];
let chartType = localStorage.getItem("si-chart-type") || "line";

/* ── THEME HELPERS ── */
function getThemeColors() {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  return {
    isLight,
    textColor:    isLight ? "#445566" : "#8899aa",
    gridColor:    isLight ? "#dde4ed" : "#1e2a38",
    bgColor:      "transparent",
    lineColor:    isLight ? "#00875a" : "#00ff9d",     // base green (overridden by trend)
    areaTop:      isLight ? "rgba(0,135,90,0.3)"  : "rgba(0,255,157,0.25)",
    areaBottom:   isLight ? "rgba(0,135,90,0.02)" : "rgba(0,255,157,0.02)",
    upColor:      isLight ? "#00875a" : "#00ff9d",
    downColor:    isLight ? "#cc2233" : "#ff3d5a",
    upBorder:     isLight ? "#00875a" : "#00ff9d",
    downBorder:   isLight ? "#cc2233" : "#ff3d5a",
    tooltipBg:    isLight ? "#ffffff" : "#0d1a26",
    tooltipBorder:isLight ? "#dde4ed" : "#1e2a38",
    tooltipText:  isLight ? "#223344" : "#c8d8e8",
  };
}

/* ── BUILD CHART (with dynamic line colour) ── */
function buildChart(data, type) {
  if (!data || !data.length) return;

  const container = document.getElementById("priceChart");
  if (!container) return;

  // Check ECharts loaded
  if (typeof echarts === "undefined") {
    container.innerHTML =
      '<div style="color:#ff3d5a;padding:20px;font-family:monospace">⚠ ECharts failed to load. Check your network connection.</div>';
    return;
  }

  // Dispose previous instance
  if (echartsInstance) {
    echartsInstance.dispose();
    echartsInstance = null;
  }

  const c = getThemeColors();
  const dates = data.map(d => d.date);

  let series, yAxisMin, yAxisMax;

  if (type === "candle") {
    // ECharts candlestick expects [open, close, low, high]
    const ohlc = data.map(d => [
      parseFloat(d.open),
      parseFloat(d.close),
      parseFloat(d.low),
      parseFloat(d.high)
    ]);

    series = [{
      name: "OHLC",
      type: "candlestick",
      data: ohlc,
      itemStyle: {
        color:        c.upColor,
        color0:       c.downColor,
        borderColor:  c.upBorder,
        borderColor0: c.downBorder,
        borderWidth: 1,
      },
    }];

    const allPrices = data.flatMap(d => [d.low, d.high]).map(Number);
    yAxisMin = Math.min(...allPrices);
    yAxisMax = Math.max(...allPrices);

  } else {
    // --- LINE / AREA: determine colour from first vs last close ---
    const firstClose = parseFloat(data[0].close);
    const lastClose  = parseFloat(data[data.length - 1].close);
    const isUp = lastClose >= firstClose;
    const lineColor = isUp ? c.upColor : c.downColor;   // green for up, red for down

    const closes = data.map(d => parseFloat(d.close));

    series = [{
      name: "Price",
      type: "line",
      data: closes,
      smooth: true,
      symbol: "none",
      lineStyle: { color: lineColor, width: 2 },
      areaStyle: {
        color: {
          type: "linear",
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: lineColor + "40" },   // semi‑transparent version
            { offset: 1, color: "transparent" }
          ]
        }
      },
      itemStyle: { color: lineColor },
    }];

    const pad = (Math.max(...closes) - Math.min(...closes)) * 0.05;
    yAxisMin = Math.min(...closes) - pad;
    yAxisMax = Math.max(...closes) + pad;
  }

  const option = {
    backgroundColor: c.bgColor,
    animation: false,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: type === "candle" ? "cross" : "line" },
      backgroundColor: c.tooltipBg,
      borderColor: c.tooltipBorder,
      textStyle: { color: c.tooltipText, fontFamily: "'Space Mono', monospace", fontSize: 11 },
      formatter: type === "candle"
        ? (params) => {
            const p = params[0];
            const [o, cl, lo, hi] = p.data;
            return `<b>${p.name}</b><br/>
                    O: ${o.toFixed(2)}&nbsp;&nbsp;H: ${hi.toFixed(2)}<br/>
                    L: ${lo.toFixed(2)}&nbsp;&nbsp;C: ${cl.toFixed(2)}`;
          }
        : undefined,
    },
    grid: {
      left: "3%", right: "3%", top: "8%", bottom: "12%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLine:  { lineStyle: { color: c.gridColor } },
      axisTick:  { lineStyle: { color: c.gridColor } },
      axisLabel: {
        color: c.textColor,
        fontFamily: "'Space Mono', monospace",
        fontSize: 10,
        rotate: 0,
        interval: Math.floor(dates.length / 6),
        formatter: (val) => val.slice(5),
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      scale: true,
      min: yAxisMin,
      max: yAxisMax,
      axisLine:  { show: false },
      axisTick:  { show: false },
      axisLabel: {
        color: c.textColor,
        fontFamily: "'Space Mono', monospace",
        fontSize: 10,
        formatter: (val) => "$" + val.toFixed(0),
      },
      splitLine: { lineStyle: { color: c.gridColor, type: "dashed" } },
    },
    dataZoom: [
      {
        type: "inside",
        start: 0, end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
      },
    ],
    series,
  };

  echartsInstance = echarts.init(container, null, { renderer: "canvas" });
  echartsInstance.setOption(option);

  // Responsive resize
  window.addEventListener("resize", () => {
    if (echartsInstance) echartsInstance.resize();
  });
}

/* ── PUBLIC API ── */
function initPriceChart(data) {
  storedData = data;
  buildChart(data, chartType);
  syncToggleButtons(chartType);
}

function setChartType(type) {
  chartType = type;
  localStorage.setItem("si-chart-type", type);
  buildChart(storedData, type);
  syncToggleButtons(type);
}

function updateChartTheme() {
  if (storedData.length) buildChart(storedData, chartType);
}

function syncToggleButtons(type) {
  const btnLine   = document.getElementById("btnLine");
  const btnCandle = document.getElementById("btnCandle");
  if (!btnLine || !btnCandle) return;
  btnLine.classList.toggle("ct-btn-active",   type === "line");
  btnCandle.classList.toggle("ct-btn-active", type === "candle");
}

/* ── TIMEFRAME BUTTONS ── */
async function loadChartData(ticker, period) {
  try {
    const res = await fetch(`/api/chart_data?ticker=${encodeURIComponent(ticker)}&period=${period}`);
    if (!res.ok) throw new Error("Fetch failed: " + res.status);
    const json = await res.json();
    if (json.chartData && json.chartData.length) {
      storedData = json.chartData;
      buildChart(storedData, chartType);
    } else {
      console.warn("No chart data returned for", ticker, period);
    }
  } catch (err) {
    console.error("Chart data error:", err);
  }
}

function initTimeframeButtons(ticker, currentPeriod) {
  const buttons = document.querySelectorAll(".tf-btn");
  if (!buttons.length) return;
  buttons.forEach(btn => {
    if (btn.dataset.period === currentPeriod) btn.classList.add("active");
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const period = btn.dataset.period;
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const url = new URL(window.location.href);
      url.searchParams.set("period", period);
      window.history.pushState({}, "", url);
      await loadChartData(ticker, period);
    });
  });
}

/* ── AUTOCOMPLETE ── */
function initAutocomplete(inputId, suggestionsId) {
  const input = document.getElementById(inputId);
  const box   = document.getElementById(suggestionsId);
  if (!input || !box) return;
  let debounceTimer;
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 1) { box.style.display = "none"; return; }
    debounceTimer = setTimeout(async () => {
      try {
        const res  = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        renderSuggestions(data, box, input);
      } catch (e) { box.style.display = "none"; }
    }, 180);
  });
  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !box.contains(e.target)) box.style.display = "none";
  });
}

function renderSuggestions(items, box, input) {
  if (!items.length) { box.style.display = "none"; return; }
  box.innerHTML = items.map(item => `
    <div class="suggestion-item" data-ticker="${item.ticker}">
      <span class="sug-ticker">${item.ticker}</span>
      <span class="sug-name">${item.name}</span>
    </div>
  `).join("");
  box.style.display = "block";
  box.querySelectorAll(".suggestion-item").forEach(el => {
    el.addEventListener("click", () => {
      input.value = el.dataset.ticker;
      box.style.display = "none";
      input.closest("form").submit();
    });
  });
}

/* ── FOOTER CLOCK ── */
function startClock() {
  const el = document.getElementById("footerTime");
  if (!el) return;
  const update = () => { el.textContent = new Date().toUTCString().replace(" GMT", " UTC"); };
  update();
  setInterval(update, 1000);
}

/* ── FLASH AUTO-DISMISS ── */
function initFlashDismiss() {
  document.querySelectorAll(".si-alert").forEach(el => {
    setTimeout(() => {
      el.style.transition = "opacity 0.5s, transform 0.5s";
      el.style.opacity = "0";
      el.style.transform = "translateY(-8px)";
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
}

/* ── THEME TOGGLE ── */
function initThemeToggle() {
  const btn   = document.getElementById("themeToggle");
  const icon  = document.getElementById("themeIcon");
  const label = document.getElementById("themeLabel");
  if (!btn) return;

  const saved = localStorage.getItem("si-theme") || "dark";
  applyTheme(saved);

  btn.addEventListener("click", () => {
    const next = (document.documentElement.getAttribute("data-theme") || "dark") === "dark"
      ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("si-theme", next);
    updateChartTheme();
  });

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    icon.textContent  = theme === "light" ? "🌙" : "☀️";
    label.textContent = theme === "light" ? "DARK" : "LIGHT";
    btn.title         = theme === "light" ? "Switch to dark mode" : "Switch to light mode";
  }
}

/* ── INIT ── */
document.addEventListener("DOMContentLoaded", () => {
  initThemeToggle();
  initAutocomplete("navTicker", "suggestions");
  startClock();
  initFlashDismiss();
  if (typeof currentTicker !== "undefined" && currentTicker) {
    initTimeframeButtons(currentTicker, currentPeriod || "1mo");
  }
});