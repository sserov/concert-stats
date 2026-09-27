const { test } = require("node:test");
const assert = require("node:assert");
const S = require("../../src/concert_stats/dashboard_app.js");

const AGG = {
  seasons: ["2016/17", "2017/18", "2026/27"],
  current_season: "2026/27",
  season_totals: {
    "2016/17": { total: 10, with_text: 8, with_composers: 6,
      meloman: { total: 6, with_text: 5, with_composers: 4 },
      mosconsv: { total: 4, with_text: 3, with_composers: 2 } },
    "2017/18": { total: 20, with_text: 18, with_composers: 16,
      meloman: { total: 12, with_text: 11, with_composers: 10 },
      mosconsv: { total: 8, with_text: 7, with_composers: 6 } },
    "2026/27": { total: 5, with_text: 5, with_composers: 5,
      meloman: { total: 3, with_text: 3, with_composers: 3 },
      mosconsv: { total: 2, with_text: 2, with_composers: 2 } },
  },
  composer_totals: {
    bach: { total: 12, meloman: 7, mosconsv: 5 },
    mozart: { total: 6, meloman: 6, mosconsv: 0 },
  },
  composer_by_season: {
    bach: { "2016/17": 3, "2017/18": 8, "2026/27": 1 },
    mozart: { "2016/17": 6 },
  },
  composer_by_season_by_hall: {
    bach: { "2016/17": { meloman: 1, mosconsv: 2 },
            "2017/18": { meloman: 5, mosconsv: 3 },
            "2026/27": { meloman: 1, mosconsv: 0 } },
  },
  coverage_by_season: [],
  jubilees: [{ cid: "bach", season: "2017/18", year: 2017, label: "К юбилею" }],
};
const COMPOSERS = { bach: { name: "И. С. Бах", born: 1685, died: 1750 },
                    mozart: { name: "В. А. Моцарт", born: 1756, died: 1791 } };
const baseState = { hall: "all", seasonFrom: "2016/17", seasonTo: "2026/27",
                    metric: "share", selected: [], heatmapExtra: 0 };
const meta = { composers: COMPOSERS };

test("share uses hall-specific denominator", () => {
  const t = S.getComposerTrend(AGG, { ...baseState, hall: "meloman" }, ["bach"], meta);
  // 2016/17: meloman bach=1, meloman total=6 → ~16.7%
  assert.ok(Math.abs(t[0].values[0] - 100 * 1 / 6) < 1e-9);
});

test("missing season yields null, not zero", () => {
  const t = S.getComposerTrend(AGG, baseState, ["mozart"], meta);
  assert.strictEqual(t[0].values[1], null);
  assert.strictEqual(t[0].values[0], 60);
});

test("delta excludes current season", () => {
  const r = S.getComposerRanking(AGG, baseState, meta);
  const bach = r.find((x) => x.cid === "bach");
  // last completed = 2017/18 (40%), first = 2016/17 (30%) → +10
  assert.ok(Math.abs(bach.deltaFirstSeason - 10) < 1e-9);
});

test("heatmap forces selected composers into rows", () => {
  const h = S.getHeatmapData(AGG, { ...baseState, selected: ["mozart"] }, 1, meta);
  const ids = h.rows.map((r) => r.cid);
  assert.ok(ids.includes("mozart"));
  assert.strictEqual(h.rows.length, 2); // top1 (bach) + forced mozart
});

test("season range clamps", () => {
  const s = S.seasonsInRange(AGG, { ...baseState, seasonFrom: "2017/18", seasonTo: "2017/18" });
  assert.deepStrictEqual(s, ["2017/18"]);
});

test("scopeTotals respects hall", () => {
  const t = S.scopeTotals(AGG, { ...baseState, hall: "mosconsv" });
  assert.strictEqual(t.total, 14);
});

test("selection capped at 6 with flag", () => {
  const sel = [];
  const a1 = S.addSelected(sel, "a"); const a2 = S.addSelected(sel, "b");
  ["c", "d", "e", "f"].forEach((c) => S.addSelected(sel, c));
  const a7 = S.addSelected(sel, "g");
  assert.strictEqual(sel.length, 6);
  assert.strictEqual(a7, false); // отклонён
  assert.strictEqual(a1 && a2, true);
});

test("addSelected ignores duplicates", () => {
  const sel = ["a"];
  assert.strictEqual(S.addSelected(sel, "a"), false);
  assert.deepStrictEqual(sel, ["a"]);
});

test("removeSelected toggles off", () => {
  const sel = ["a", "b"];
  S.removeSelected(sel, "a");
  assert.deepStrictEqual(sel, ["b"]);
});

test("effectiveSelection defaults to top-5 without mutating state", () => {
  const st = { ...baseState, selected: [] };
  assert.deepStrictEqual(S.effectiveSelection(AGG, st, meta), ["bach", "mozart"]);
  assert.deepStrictEqual(st.selected, []);
  assert.deepStrictEqual(
    S.effectiveSelection(AGG, { ...baseState, selected: ["mozart"] }, meta), ["mozart"]);
});

test("trendViewModel caps traces and carries counts per point", () => {
  const vm = S.trendViewModel(AGG, { ...baseState, selected: ["bach", "mozart", "x1", "x2", "x3", "x4", "x5"] }, meta);
  assert.ok(vm.traces.length <= 6);
  for (const tr of vm.traces) {
    assert.strictEqual(tr.shares.length, vm.x.length);
    for (let i = 0; i < tr.shares.length; i++) assert.ok(tr.counts[i] !== undefined);
  }
  const vmCount = S.trendViewModel(AGG, { ...baseState, metric: "count", selected: ["bach"] }, meta);
  assert.deepStrictEqual(vmCount.traces[0].values, vmCount.traces[0].counts);
});

test("rankingViewModel sorts and limits rows", () => {
  const rows = [
    { cid: "mozart", name: "Моцарт", count: 6, share: 17, delta: null },
    { cid: "bach", name: "Бах", count: 12, share: 34, delta: 10 },
    { cid: "haydn", name: "Гайдн", count: 9, share: 25, delta: -2 },
  ];
  const vm = S.rankingViewModel(rows, { sortKey: "count", sortDir: "desc", query: "", limit: 2 });
  assert.deepStrictEqual(vm.rows.map((r) => r.cid), ["bach", "haydn"]);
  const byName = S.rankingViewModel(rows, { sortKey: "name", sortDir: "asc", query: "", limit: 3 });
  assert.deepStrictEqual(byName.rows.map((r) => r.name), ["Бах", "Гайдн", "Моцарт"]);
  const filtered = S.rankingViewModel(rows, { sortKey: "share", sortDir: "desc", query: "ба", limit: 3 });
  assert.deepStrictEqual(filtered.rows.map((r) => r.cid), ["bach"]);
});

test("delta is null with a single completed season", () => {
  const r = S.getComposerRanking(
    AGG, { ...baseState, seasonFrom: "2026/27", seasonTo: "2026/27" }, meta);
  assert.strictEqual(r.find((x) => x.cid === "bach").deltaFirstSeason, null);
});

test("fmtDelta formats russian percentage points", () => {
  assert.strictEqual(S.fmtDelta(3.14), "+3,1 п.п.");
  assert.strictEqual(S.fmtDelta(-2.05), "−2,1 п.п.");
  assert.strictEqual(S.fmtDelta(null), "—");
});

test("heatmap keeps top-15 plus forced selected out of 20 composers", () => {
  const seasons = ["2016/17", "2017/18"];
  const names = {};
  const totals = {};
  const bySeason = {};
  const totalBySeason = { "2016/17": 100, "2017/18": 100 };
  for (let i = 0; i < 20; i++) {
    const cid = `c${i}`;
    names[cid] = { name: `Композитор ${i}`, born: null, died: null };
    bySeason[cid] = { "2016/17": 20 - i, "2017/18": 20 - i };
    totals[cid] = { total: 2 * (20 - i), meloman: 20 - i, mosconsv: 20 - i };
  }
  const big = {
    seasons,
    current_season: null,
    season_totals: {
      "2016/17": { total: 100, with_text: 90, with_composers: 80,
        meloman: { total: 50, with_text: 45, with_composers: 40 },
        mosconsv: { total: 50, with_text: 45, with_composers: 40 } },
      "2017/18": { total: 100, with_text: 90, with_composers: 80,
        meloman: { total: 50, with_text: 45, with_composers: 40 },
        mosconsv: { total: 50, with_text: 45, with_composers: 40 } },
    },
    composer_totals: totals,
    composer_by_season: bySeason,
    composer_by_season_by_hall: {},
    coverage_by_season: [],
    jubilees: [],
  };
  void totalBySeason;
  const st = { ...baseState, seasonFrom: "2016/17", seasonTo: "2017/18", selected: ["c17"] };
  const h = S.getHeatmapData(big, st, 15, { composers: names });
  assert.strictEqual(h.rows.length, 16);
  assert.ok(h.rows.map((r) => r.cid).includes("c17"));
  assert.deepStrictEqual(h.forced, ["c17"]);
});

test("getHallComparison uses per-hall denominators", () => {
  const hc = S.getHallComparison(AGG, baseState, "bach", meta);
  assert.deepStrictEqual(hc.seasons, ["2016/17", "2017/18", "2026/27"]);
  assert.ok(Math.abs(hc.phil[0] - 100 * 1 / 6) < 1e-9);
  assert.ok(Math.abs(hc.cons[0] - 100 * 2 / 4) < 1e-9);
  assert.strictEqual(hc.philTotal, 7);
  assert.strictEqual(hc.consTotal, 5);
  assert.ok(Math.abs(hc.philShare - 100 * 7 / 21) < 1e-9);
  assert.ok(Math.abs(hc.consShare - 100 * 5 / 14) < 1e-9);
});

test("heatmap metric is independent of trend metric", () => {
  const asShare = S.getHeatmapData(
    AGG, { ...baseState, metric: "count", heatmapMetric: "share" }, 1, meta);
  assert.strictEqual(asShare.rows[0].values[0], 30); // bach 2016/17: 3/10
  const asCount = S.getHeatmapData(
    AGG, { ...baseState, metric: "share", heatmapMetric: "count" }, 1, meta);
  assert.strictEqual(asCount.rows[0].values[0], 3);
});

test("_heatClickRow resolves row from flat or array pointIndex", () => {
  const rows = [{ cid: "a" }, { cid: "b" }, { cid: "c" }, { cid: "d" }];
  assert.strictEqual(S._heatClickRow(rows, 3).cid, "d");
  assert.strictEqual(S._heatClickRow(rows, [3, 5]).cid, "d");
  assert.strictEqual(S._heatClickRow(rows, "0,3"), null);
  assert.strictEqual(S._heatClickRow(rows, 99), null);
  assert.strictEqual(S._heatClickRow(rows, -1), null);
});

test("rankingViewModel sorts by deltaFirstSeason", () => {
  const rows = [
    { cid: "a", name: "A", deltaFirstSeason: 5 },
    { cid: "b", name: "B", deltaFirstSeason: -2 },
    { cid: "c", name: "C", deltaFirstSeason: null },
  ];
  const vm = S.rankingViewModel(
    rows, { sortKey: "deltaFirstSeason", sortDir: "desc", query: "", limit: 3 });
  assert.deepStrictEqual(vm.rows.map((r) => r.cid), ["a", "b", "c"]);
});

test("selectComposer distinguishes duplicate from cap", () => {
  const sel = [];
  assert.strictEqual(S.selectComposer(sel, "a"), "added");
  assert.strictEqual(S.selectComposer(sel, "a"), "duplicate");
  assert.deepStrictEqual(sel, ["a"]);
  for (let i = 0; i < 5; i++) S.selectComposer(sel, "x" + i);
  assert.strictEqual(S.selectComposer(sel, "z"), "capped");
  assert.strictEqual(sel.length, 6);
});

test("seasonTickLabel marks the current season", () => {
  assert.strictEqual(S.seasonTickLabel("2026/27", AGG), "2026/27 (тек.)");
  assert.strictEqual(S.seasonTickLabel("2016/17", AGG), "2016/17");
});
