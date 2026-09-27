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
