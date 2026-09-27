/* Dashboard app: pure selectors first, DOM/Plotly renderers below.
 * Loaded inline after window.DATASET / window.AGGREGATES. */
"use strict";

const MAX_SELECTED = 6;
/* Slots 1–3 are the spec hall/jubilee tokens; 4–6 re-stepped to pass CVD and
 * normal-vision separation checks on the #F7F5F0 surface (dataviz validator). */
const PALETTE = ["#8C2635", "#536B63", "#A77A2B", "#4E6FA3", "#6E4A38", "#5F8248"];
const MARKERS = ["circle", "diamond", "square", "triangle-up", "cross", "x"];

/* ---------- helpers ---------- */

function _meta(meta) {
  if (meta && meta.composers) return meta;
  if (typeof window !== "undefined" && window.DATASET && window.DATASET.composers) {
    return { composers: window.DATASET.composers };
  }
  return { composers: {} };
}

function _name(meta, cid) {
  const c = meta.composers[cid];
  return c ? c.name : cid;
}

function _share(n, d) {
  return d > 0 ? 100 * n / d : null;
}

/* Per-hall season totals; hall "all" → the season dict itself. */
function _hallTotals(AGG, season, hall) {
  const st = AGG.season_totals[season];
  return hall === "all" ? st : st[hall];
}

/* Composer concert count for a season within the hall scope. */
function _composerCount(AGG, cid, season, hall) {
  if (hall === "all") {
    const per = AGG.composer_by_season[cid];
    return per && per[season] ? per[season] : 0;
  }
  const per = AGG.composer_by_season_by_hall[cid];
  const row = per && per[season];
  return row && row[hall] ? row[hall] : 0;
}

function _isCurrent(AGG, season) {
  return season === AGG.current_season;
}

function _fmtRu(x, digits) {
  if (x === null || x === undefined) return "—";
  return x.toLocaleString("ru-RU", {
    minimumFractionDigits: digits || 0, maximumFractionDigits: digits || 0,
  });
}

/* ---------- selectors (pure, no DOM/Plotly) ---------- */

function seasonsInRange(AGG, state) {
  const from = AGG.seasons.indexOf(state.seasonFrom);
  const to = AGG.seasons.indexOf(state.seasonTo);
  if (from < 0 || to < 0 || to < from) return [];
  return AGG.seasons.slice(from, to + 1);
}

function scopeTotals(AGG, state) {
  const out = { total: 0, withText: 0, withComposers: 0 };
  for (const s of seasonsInRange(AGG, state)) {
    const t = _hallTotals(AGG, s, state.hall);
    if (!t) continue;
    out.total += t.total;
    out.withText += t.with_text;
    out.withComposers += t.with_composers;
  }
  return out;
}

/* Sum of the composer's concerts within hall scope over the season range. */
function _composerScopeTotal(AGG, cid, state) {
  let n = 0;
  for (const s of seasonsInRange(AGG, state)) n += _composerCount(AGG, cid, s, state.hall);
  return n;
}

function getComposerRanking(AGG, state, meta) {
  meta = _meta(meta);
  const totals = scopeTotals(AGG, state);
  const range = seasonsInRange(AGG, state);
  const rows = [];
  for (const cid of Object.keys(AGG.composer_totals)) {
    const count = _composerScopeTotal(AGG, cid, state);
    if (count === 0) continue;
    const share = _share(count, totals.total);
    const sparkline = range.map((s) =>
      _share(_composerCount(AGG, cid, s, state.hall), _hallTotals(AGG, s, state.hall).total));
    const completed = range.filter((s) => !_isCurrent(AGG, s));
    const first = completed[0];
    const last = completed[completed.length - 1];
    let delta = null;
    if (first && last && first !== last) {
      const a = _share(_composerCount(AGG, cid, first, state.hall), _hallTotals(AGG, first, state.hall).total);
      const b = _share(_composerCount(AGG, cid, last, state.hall), _hallTotals(AGG, last, state.hall).total);
      if (a !== null && b !== null) delta = b - a;
    }
    rows.push({ cid, name: _name(meta, cid), share, count, deltaFirstSeason: delta, sparkline });
  }
  return rows.sort((a, b) => b.share - a.share);
}

function getComposerTrend(AGG, state, cids, meta) {
  meta = _meta(meta);
  const range = seasonsInRange(AGG, state);
  return cids.map((cid) => ({
    cid,
    name: _name(meta, cid),
    values: range.map((s) => {
      const n = _composerCount(AGG, cid, s, state.hall);
      if (state.metric === "count") return n;
      return n === 0 ? null : _share(n, _hallTotals(AGG, s, state.hall).total);
    }),
  }));
}

function getHeatmapData(AGG, state, rowLimit, meta) {
  meta = _meta(meta);
  const ranking = getComposerRanking(AGG, state, meta);
  const top = ranking.slice(0, rowLimit);
  const inTop = new Set(top.map((r) => r.cid));
  const forced = state.selected.filter((cid) => !inTop.has(cid));
  const chosen = ranking.filter((r) => inTop.has(r.cid) || forced.includes(r.cid));
  const range = seasonsInRange(AGG, state);
  const rows = chosen.map((r) => ({
    cid: r.cid,
    name: r.name,
    values: range.map((s) => {
      const n = _composerCount(AGG, r.cid, s, state.hall);
      if (state.metric === "count") return n;
      return n === 0 ? null : _share(n, _hallTotals(AGG, s, state.hall).total);
    }),
  }));
  return { rows, forced };
}

function getHallComparison(AGG, state, cid, meta) {
  meta = _meta(meta);
  const range = seasonsInRange(AGG, state);
  const series = (hall) => range.map((s) => {
    const n = _composerCount(AGG, cid, s, hall);
    return n === 0 ? null : _share(n, _hallTotals(AGG, s, hall).total);
  });
  const totals = (hall) => {
    let n = 0;
    for (const s of range) n += _composerCount(AGG, cid, s, hall);
    return n;
  };
  const seasonSum = (hall) => {
    let n = 0;
    for (const s of range) n += _hallTotals(AGG, s, hall).total;
    return n;
  };
  const philTotal = totals("meloman");
  const consTotal = totals("mosconsv");
  return {
    seasons: range,
    phil: series("meloman"),
    cons: series("mosconsv"),
    philTotal,
    consTotal,
    philShare: _share(philTotal, seasonSum("meloman")),
    consShare: _share(consTotal, seasonSum("mosconsv")),
  };
}

function getCoverage(AGG) {
  return AGG.coverage_by_season;
}

function jubileeMap(AGG) {
  const map = {};
  for (const j of AGG.jubilees) map[`${j.cid}|${j.season}`] = j.label;
  return map;
}

/* Explicit selection, or the top-5 default when nothing is chosen. */
function effectiveSelection(AGG, state, meta) {
  if (state.selected.length > 0) return state.selected.slice();
  return getComposerRanking(AGG, state, meta).slice(0, 5).map((r) => r.cid);
}

/* View-model for the main trend chart: one trace per selected composer,
 * plus jubilee annotations and the COVID band range. */
function trendViewModel(AGG, state, meta) {
  meta = _meta(meta);
  const cids = effectiveSelection(AGG, state, meta).slice(0, MAX_SELECTED);
  const range = seasonsInRange(AGG, state);
  const trends = getComposerTrend(AGG, { ...state, metric: "share" }, cids, meta);
  const counts = getComposerTrend(AGG, { ...state, metric: "count" }, cids, meta);
  const jMap = jubileeMap(AGG);
  const traces = cids.map((cid, i) => {
    const tr = trends.find((t) => t.cid === cid);
    const ct = counts.find((t) => t.cid === cid);
    return {
      cid,
      name: _name(meta, cid),
      color: PALETTE[i % PALETTE.length],
      symbol: MARKERS[i % MARKERS.length],
      shares: tr ? tr.values : range.map(() => null),
      counts: ct ? ct.values : range.map(() => 0),
      values: state.metric === "count" ? (ct ? ct.values : []) : (tr ? tr.values : []),
    };
  });
  const annotations = [];
  traces.forEach((tr) => {
    range.forEach((s, i) => {
      const label = jMap[`${tr.cid}|${s}`];
      if (label && tr.shares[i] !== null) {
        annotations.push({ x: s, y: tr.shares[i], text: label, cid: tr.cid });
      }
    });
  });
  return { x: range, traces, annotations, covidRange: ["2019/20", "2020/21"] };
}

/* ---------- selection state (pure mutations) ---------- */

function addSelected(sel, cid) {
  if (sel.includes(cid)) return false;
  if (sel.length >= MAX_SELECTED) return false;
  sel.push(cid);
  return true;
}

function removeSelected(sel, cid) {
  const i = sel.indexOf(cid);
  if (i >= 0) sel.splice(i, 1);
  return i >= 0;
}

/* ---------- app state + rendering (browser only) ---------- */

const RENDERERS = [];
let AGG = null;
let META = { composers: {} };
let state = null;
let toastTimer = null;

function $id(id) { return document.getElementById(id); }

function showToast(msg) {
  const t = $id("toast");
  t.textContent = msg;
  t.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2500);
}

function renderKPIs() {
  const totals = scopeTotals(AGG, state);
  const composers = getComposerRanking(AGG, state, META).length;
  $id("kpi-concerts").textContent = _fmtRu(totals.total);
  $id("kpi-composers").textContent = _fmtRu(composers);
  $id("kpi-coverage").textContent =
    _fmtRu(_share(totals.withComposers, totals.withText), 1) + "%";
  $id("kpi-unknown").textContent =
    _fmtRu(_share(totals.total - totals.withComposers, totals.total), 1) + "%";
}

function renderChips() {
  const wrap = $id("chips");
  wrap.textContent = "";
  state.selected.forEach((cid, i) => {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.dataset.cid = cid;
    chip.setAttribute("aria-label", `Убрать ${_name(META, cid)} из выбора`);
    const swatch = document.createElement("span");
    swatch.className = "chip-swatch";
    swatch.style.background = PALETTE[i % PALETTE.length];
    const label = document.createElement("span");
    label.textContent = _name(META, cid);
    const x = document.createElement("span");
    x.className = "chip-x";
    x.textContent = "×";
    x.setAttribute("aria-hidden", "true");
    chip.append(swatch, label, x);
    wrap.append(chip);
  });
}

/* Autocomplete: filter by name substring, keyboard navigation. */
const AC_STATE = { items: [], active: -1 };

function acClose() {
  $id("search-ac").hidden = true;
  $id("composer-search").setAttribute("aria-expanded", "false");
  AC_STATE.items = [];
  AC_STATE.active = -1;
}

function acPick(cid) {
  if (addSelected(state.selected, cid)) {
    renderAll();
  } else if (state.selected.length >= MAX_SELECTED && !state.selected.includes(cid)) {
    showToast("Максимум 6 композиторов");
  }
  $id("composer-search").value = "";
  acClose();
}

function acRender(q) {
  const qLower = q.trim().toLowerCase();
  if (!qLower) { acClose(); return; }
  AC_STATE.items = Object.keys(META.composers)
    .filter((cid) => _name(META, cid).toLowerCase().includes(qLower))
    .slice(0, 8);
  const ul = $id("search-ac");
  ul.textContent = "";
  AC_STATE.items.forEach((cid, i) => {
    const li = document.createElement("li");
    li.id = `ac-opt-${i}`;
    li.role = "option";
    li.setAttribute("aria-selected", i === AC_STATE.active ? "true" : "false");
    li.textContent = _name(META, cid);
    li.addEventListener("click", () => acPick(cid));
    ul.append(li);
  });
  ul.hidden = AC_STATE.items.length === 0;
  $id("composer-search").setAttribute("aria-expanded", String(!ul.hidden));
}

function acMove(delta) {
  if (!AC_STATE.items.length) return;
  AC_STATE.active = Math.min(Math.max(AC_STATE.active + delta, 0), AC_STATE.items.length - 1);
  acRender($id("composer-search").value);
}

function bindAutocomplete() {
  const input = $id("composer-search");
  input.addEventListener("input", () => { AC_STATE.active = -1; acRender(input.value); });
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { ev.preventDefault(); acMove(1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); acMove(-1); }
    else if (ev.key === "Enter") {
      ev.preventDefault();
      const cid = AC_STATE.items[AC_STATE.active >= 0 ? AC_STATE.active : 0];
      if (cid) acPick(cid);
    } else if (ev.key === "Escape") { acClose(); }
  });
  input.addEventListener("blur", () => setTimeout(acClose, 150));
}

function bindControls() {
  $id("hall-seg").addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-hall]");
    if (!btn) return;
    state.hall = btn.dataset.hall;
    $id("hall-seg").querySelectorAll(".seg-btn").forEach((b) =>
      b.setAttribute("aria-pressed", String(b === btn)));
    renderAll();
  });
  $id("metric-seg").addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-metric]");
    if (!btn) return;
    state.metric = btn.dataset.metric;
    $id("metric-seg").querySelectorAll(".seg-btn").forEach((b) =>
      b.setAttribute("aria-pressed", String(b === btn)));
    renderAll();
  });
  const from = $id("season-from");
  const to = $id("season-to");
  from.addEventListener("change", () => {
    state.seasonFrom = from.value;
    if (AGG.seasons.indexOf(to.value) < AGG.seasons.indexOf(from.value)) {
      state.seasonTo = from.value;
      to.value = from.value;
    }
    renderAll();
  });
  to.addEventListener("change", () => {
    state.seasonTo = to.value;
    if (AGG.seasons.indexOf(from.value) > AGG.seasons.indexOf(to.value)) {
      state.seasonFrom = to.value;
      from.value = to.value;
    }
    renderAll();
  });
  $id("chips").addEventListener("click", (ev) => {
    const chip = ev.target.closest(".chip");
    if (!chip) return;
    removeSelected(state.selected, chip.dataset.cid);
    renderAll();
  });
  bindAutocomplete();
}

function init() {
  AGG = window.AGGREGATES;
  META = _meta();
  state = {
    hall: "all",
    seasonFrom: AGG.seasons[0],
    seasonTo: AGG.current_season,
    metric: "share",
    selected: [],
    heatmapExtra: 15,
    rankingLimit: 50,
    rankingSortKey: "share",
    rankingSortDir: "desc",
    rankingQuery: "",
  };
  for (const sel of [$id("season-from"), $id("season-to")]) {
    for (const s of AGG.seasons) {
      const o = document.createElement("option");
      o.value = s;
      o.textContent = s;
      sel.append(o);
    }
  }
  $id("season-to").value = AGG.current_season;
  bindControls();
  $id("about-open").addEventListener("click", () => $id("about").showModal());
  $id("about").addEventListener("click", (ev) => {
    if (ev.target.closest("[data-close]") || ev.target === $id("about")) $id("about").close();
  });
  renderAll();
}

function renderAll() {
  renderKPIs();
  renderChips();
  for (const fn of RENDERERS) fn();
}

/* ---------- renderTrend: the dominant chart ---------- */

function _trendExtra(i, range, cid, tr) {
  const s = range[i];
  const parts = [];
  if (state.hall === "all") {
    const mel = _composerCount(AGG, cid, s, "meloman");
    const cons = _composerCount(AGG, cid, s, "mosconsv");
    parts.push(`филармония ${mel} · консерватория ${cons}`);
  }
  const j = jubileeMap(AGG)[`${cid}|${s}`];
  if (j) parts.push(j);
  if (s === AGG.current_season) parts.push("Сезон продолжается; данные неполные");
  return parts.length ? "<br>" + parts.join("<br>") : "";
}

function _trendTraces(vm) {
  return vm.traces.map((tr) => ({
    type: "scatter",
    mode: "lines+markers",
    name: tr.name,
    meta: [tr.cid],
    x: vm.x,
    y: tr.values,
    line: { color: tr.color, width: 2, shape: "spline" },
    marker: { symbol: tr.symbol, size: 7, color: tr.color },
    connectgaps: false,
    customdata: tr.values.map((v, i) => [
      tr.shares[i] === null ? "—" : `${_fmtRu(tr.shares[i], 1)}%`,
      tr.counts[i],
      _trendExtra(i, vm.x, tr.cid, tr),
    ]),
    hovertemplate:
      "Сезон %{x}<br>%{fullData.name}<br>%{customdata[0]}<br>" +
      "концертов: %{customdata[1]}%{customdata[2]}<extra></extra>",
  }));
}

function _trendLayout(vm) {
  const isShare = state.metric === "share";
  const ticktext = vm.x.map((s) => (s === AGG.current_season ? `${s} (тек.)` : s));
  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "-apple-system, 'Segoe UI', Roboto, sans-serif", color: "#22211F", size: 13 },
    margin: { l: 64, r: 24, t: 24, b: 48 },
    showlegend: true,
    legend: { orientation: "h", y: -0.15 },
    xaxis: {
      tickvals: vm.x, ticktext, ticklen: 4,
      gridcolor: "#DDD9D0", linecolor: "#DDD9D0",
    },
    yaxis: isShare
      ? { title: { text: "% концертов сезона" }, ticksuffix: "%", gridcolor: "#DDD9D0", range: [0, null] }
      : { title: { text: "концертов за сезон" }, tickformat: ",d", gridcolor: "#DDD9D0", range: [0, null] },
    hovermode: "x unified",
    shapes: [{
      type: "rect", x0: vm.covidRange[0], x1: vm.covidRange[1],
      yref: "paper", y0: 0, y1: 1,
      fillcolor: "#77736B", opacity: 0.06, line: { width: 0 },
    }],
    annotations: [
      {
        x: vm.covidRange[0], y: 1, yref: "paper", text: "ковид",
        showarrow: false, font: { color: "#77736B", size: 11 }, yshift: 10,
      },
      ...vm.annotations.map((a) => ({
        x: a.x, y: a.y, text: a.text, showarrow: true, arrowhead: 2, arrowsize: 0.6,
        arrowwidth: 0.8, arrowcolor: "#A77A2B",
        font: { color: "#22211F", size: 10 },
        bgcolor: "rgba(167,122,43,0.15)", ay: -24,
      })),
    ],
  };
  return layout;
}

function renderTrend() {
  const vm = trendViewModel(AGG, state, META);
  const div = $id("trend-plot");
  const total = scopeTotals(AGG, state).total;
  const top = vm.traces
    .map((tr) => {
      const n = tr.counts.reduce((a, b) => a + b, 0);
      return `${tr.name} ${_fmtRu(_share(n, total), 1)}%`;
    })
    .slice(0, 3)
    .join(", ");
  $id("trend-summary").textContent =
    `В выборке ${_fmtRu(total)} концертов; лидеры диапазона: ${top}`;
  const cfg = { displayModeBar: false, responsive: true };
  Plotly.newPlot(div, _trendTraces(vm), _trendLayout(vm), cfg).then(() => {
    if (!div._clickBound) {
      div._clickBound = true;
      div.on("plotly_click", (ev) => {
        const cid = ev.points[0] && ev.points[0].meta && ev.points[0].meta[0];
        if (cid && typeof openComposerDrawer === "function") openComposerDrawer(cid);
      });
    }
  });
}

/* ---------- node:test exports (no DOM at module scope) ---------- */

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
    effectiveSelection, addSelected, removeSelected, trendViewModel,
  };
}
if (typeof document !== "undefined" && typeof window !== "undefined") {
  window.DashApp = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
    effectiveSelection, addSelected, removeSelected, trendViewModel, init,
  };
}
/* Script tag sits at the end of <body>: DOM exists, safe to register renders. */
if (typeof document !== "undefined" && typeof window !== "undefined") {
  RENDERERS.push(renderTrend);
  window.addEventListener("load", init);
}
