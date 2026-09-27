/* Dashboard app: pure selectors first, DOM/Plotly renderers below.
 * Loaded inline after window.DATASET / window.AGGREGATES. */
"use strict";

const MAX_SELECTED = 6;
const PALETTE = ["#8C2635", "#536B63", "#A77A2B", "#3E5C76", "#7A5C3E", "#4F6228"];

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

/* ---------- node:test exports (no DOM at module scope) ---------- */

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
    effectiveSelection, addSelected, removeSelected,
  };
}
if (typeof document !== "undefined" && typeof window !== "undefined") {
  window.DashApp = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
    effectiveSelection, addSelected, removeSelected, init,
  };
}
