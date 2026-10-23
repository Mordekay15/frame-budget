// summary.md: one row per architecture x deadline, pooled over skills, with 95%
// confidence intervals over games for the main metric.

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN);
function ci95(xs) {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  const sd = Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / (xs.length - 1));
  return (1.96 * sd) / Math.sqrt(xs.length);
}
const pct = (x) => (Number.isFinite(x) ? `${(100 * x).toFixed(0)}%` : "–");
const num = (x, d = 0) => (Number.isFinite(x) ? x.toFixed(d) : "–");
const vals = (rows, k) => rows.map((r) => r[k]).filter((v) => v !== null && v !== "" && Number.isFinite(+v)).map(Number);

export function summaryMarkdown(games, meta) {
  const groups = new Map();
  for (const g of games) {
    const key = `${g.arch}|${g.deadline_ms}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(g);
  }
  const order = ["rules", "blocking", "async", "cache", "prefetch"];
  const keys = [...groups.keys()].sort((a, b) => {
    const [aa, ad] = a.split("|"), [ba, bd] = b.split("|");
    return order.indexOf(aa) - order.indexOf(ba) || (+ad || 0) - (+bd || 0);
  });
  const lines = [
    "# Simulation summary",
    "",
    `Decider: **${meta.decider}** (${meta.latency}). ${meta.games} games. Seed ${meta.seed}, cache key coarseness ${meta.coarse}` +
      `${meta.sharedCache ? ", one shared cache per cell" : ""}.`,
    meta.decider === "fake" ? "\n> Fake Jev: real-shaped latencies, made-up answers. For checking the pipeline only, never thesis data.\n" : "",
    "| architecture | deadline | games | decided by model (95% CI) | fallback | mean wait | p95 wait | requests / spell | element right | rules would be right | cost / hour | worst tick |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
  ];
  for (const k of keys) {
    const rows = groups.get(k);
    const [arch, dl] = k.split("|");
    const share = vals(rows, "model_share");
    const spells = vals(rows, "spells").reduce((a, b) => a + b, 0);
    const reqs = vals(rows, "requests").reduce((a, b) => a + b, 0) + vals(rows, "prefetch_requests").reduce((a, b) => a + b, 0);
    lines.push(`| ${arch} | ${dl ? dl + " ms" : "–"} | ${rows.length} | ${pct(mean(share))} ± ${num(100 * ci95(share))} | ` +
      `${pct(mean(vals(rows, "fallback_rate")))} | ${num(mean(vals(rows, "mean_wait_ms")))} ms | ${num(mean(vals(rows, "p95_wait_ms")))} ms | ` +
      `${num(spells ? reqs / spells : NaN, 2)} | ${pct(mean(vals(rows, "element_accuracy")))} | ${pct(mean(vals(rows, "rules_element_accuracy")))} | ` +
      `$${num(mean(vals(rows, "cost_per_hour_usd")), 3)} | ${num(Math.max(...vals(rows, "worst_tick_ms")))} ms |`);
  }
  lines.push(
    "",
    "- **decided by model**: share of spells decided by Jev, the cache or a prefetch, i.e. not by the fallback rules.",
    "- **wait**: from pressing Enter to the spell being cast. Rules and cache hits are instant.",
    "- **element right**: the applied element matches the corpus label (labelled spells only). **rules would be right**: the same for the keyword rules on the same spells.",
    "- **worst tick**: the longest tick in any game of the row. The budget is 33 ms; only blocking breaks it.",
    "",
  );
  return lines.join("\n");
}
