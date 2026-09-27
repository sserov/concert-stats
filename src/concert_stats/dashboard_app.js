/* Dashboard app: pure selectors first, DOM/Plotly renderers below.
 * Loaded inline after window.DATASET / window.AGGREGATES. */
"use strict";

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

/* ---------- node:test exports (no DOM at module scope) ---------- */

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
  };
}
if (typeof document !== "undefined" && typeof window !== "undefined") {
  window.DashApp = {
    seasonsInRange, scopeTotals, getComposerRanking, getComposerTrend,
    getHeatmapData, getHallComparison, getCoverage, jubileeMap,
  };
}
