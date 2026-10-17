// "What if your income changes?" Re-runs the rules-only matcher at a grid of
// incomes (POST /api/income-scenarios) and shows what the household would gain
// or lose, including the benefits cliff: earning more but ending up with less.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { getIncomeScenarios } from "../../api/benefitsApi.js";
import { Alert, Button } from "../ui/index.jsx";

const usd = (v) => `$${Math.round(v).toLocaleString()}`;
const short = (v) => (v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${Math.round(v)}`);
const signed = (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${usd(Math.abs(v))}`;
const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;

// Chart color: the site's info blue (passes the dataviz lightness and contrast checks).
const LINE = "#2378c3";
const GRID = "#dfe1e2";
const INK_MUTED = "#565c65";

const yearly = (s) => s.annual_income + s.total_estimated_monthly_value * 12;

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(640);
  useLayoutEffect(() => {
    if (!ref.current) return undefined;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

// Round up to 1, 2, 2.5 or 5 times a power of ten, so axis ticks land on even numbers.
function niceMax(v) {
  const base = 10 ** Math.floor(Math.log10(Math.max(v, 1)));
  const m = [1, 2, 2.5, 5, 10].find((k) => k * base >= v);
  return m * base;
}

const benefitsYear = (s) => s.total_estimated_monthly_value * 12;

function Chart({ scenarios, currentIndex, selected, onSelect }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);
  const height = width < 480 ? 220 : 260;
  const pad = { top: 16, right: 16, bottom: 32, left: width < 480 ? 44 : 56 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;
  const maxX = scenarios[scenarios.length - 1].annual_income || 1;
  const maxY = niceMax(Math.max(...scenarios.map(benefitsYear), 1));
  const x = (v) => pad.left + (v / maxX) * w;
  const y = (v) => pad.top + h - (v / maxY) * h;
  // Benefits change in steps at each program's limit, so draw a step line.
  const steps = scenarios
    .map((s, i) => {
      const px = x(s.annual_income).toFixed(1);
      const py = y(benefitsYear(s)).toFixed(1);
      if (!i) return `M${px},${py}`;
      return `H${px}V${py}`;
    })
    .join("");
  const area = `${steps}V${y(0)}H${x(0)}Z`;
  const xTicks = Array.from({ length: 5 }, (_, i) => (maxX / 4) * i);
  const yTicks = Array.from({ length: 5 }, (_, i) => (maxY / 4) * i);

  const nearest = (clientX) => {
    const box = ref.current.getBoundingClientRect();
    const v = ((clientX - box.left - pad.left) / w) * maxX;
    let best = 0;
    scenarios.forEach((s, i) => {
      if (Math.abs(s.annual_income - v) < Math.abs(scenarios[best].annual_income - v)) best = i;
    });
    return best;
  };
  const shown = hover ?? selected;
  const s = scenarios[shown];
  const tipLeft = Math.min(Math.max(x(s.annual_income) - 90, 0), width - 180);

  return (
    <div ref={ref} className="relative mt-4 select-none">
      <svg
        width={width}
        height={height}
        role="img"
        aria-label="Step chart of estimated benefits per year at each income. Each drop is a program ending. The table below has the same numbers."
        onPointerMove={(e) => setHover(nearest(e.clientX))}
        onPointerLeave={() => setHover(null)}
        onClick={(e) => onSelect(nearest(e.clientX))}
        className="block cursor-crosshair touch-pan-y"
        style={{ fontFamily: "var(--font-sans)" }}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={pad.left} x2={pad.left + w} y1={y(t)} y2={y(t)} stroke={GRID} />
            <text x={pad.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize="12" fill={INK_MUTED} className="tabular-nums">{short(t)}</text>
          </g>
        ))}
        {xTicks.map((t, i) => (
          <text key={t} x={x(t)} y={height - 10} textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"} fontSize="12" fill={INK_MUTED} className="tabular-nums">{short(t)}</text>
        ))}
        <path d={area} fill={LINE} fillOpacity="0.12" />
        <path d={steps} fill="none" stroke={LINE} strokeWidth="2" strokeLinejoin="round" />
        {/* Crosshair at the hovered or selected income. */}
        <line x1={x(s.annual_income)} x2={x(s.annual_income)} y1={pad.top} y2={pad.top + h} stroke={INK_MUTED} strokeWidth="1" />
        <circle cx={x(scenarios[currentIndex].annual_income)} cy={y(benefitsYear(scenarios[currentIndex]))} r="6" fill="#e5a000" stroke="#fff" strokeWidth="2" />
        <circle cx={x(s.annual_income)} cy={y(benefitsYear(s))} r="5" fill={LINE} stroke="#fff" strokeWidth="2" />
      </svg>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1 w-[180px] rounded border border-border bg-white px-3 py-2 text-sm shadow-sm"
        style={{ left: tipLeft }}
      >
        <p className="font-bold tabular-nums">{usd(benefitsYear(s))}/yr in benefits</p>
        <p className="text-muted">
          at <span className="tabular-nums">{usd(s.annual_income)}</span> income, {plural(s.program_count, "program")}
        </p>
      </div>
      <p className="mt-2 flex items-center gap-2 text-sm">
        <span className="h-3 w-3 rounded-full bg-accent" aria-hidden="true" />Your income now
      </p>
    </div>
  );
}

const LIST_LIMIT = 6;

function ProgramList({ title, ids, byId, tone }) {
  const [all, setAll] = useState(false);
  if (!ids.length) return null;
  return (
    <div>
      <h3 className="text-lg">{title}</h3>
      <ul className="mt-1 space-y-1">
        {(all ? ids : ids.slice(0, LIST_LIMIT)).map((id) => {
          const p = byId[id];
          return (
            <li key={id} className="flex justify-between gap-4">
              <span>{p.program}</span>
              <span className={`shrink-0 tabular-nums ${tone}`}>
                {p.monthly_value_usd > 0 ? `Est. ${usd(p.monthly_value_usd)}/mo` : p.category === "health" ? "Health coverage" : "Value varies"}
              </span>
            </li>
          );
        })}
      </ul>
      {ids.length > LIST_LIMIT && (
        <button type="button" className="mt-2 font-semibold text-primary underline" aria-expanded={all} onClick={() => setAll((a) => !a)}>
          {all ? "Show fewer" : `Show all ${ids.length}`}
        </button>
      )}
    </div>
  );
}

export default function IncomeWhatIf({ profile }) {
  const [state, setState] = useState({ status: "loading" });
  const [selected, setSelected] = useState(null);
  const key = JSON.stringify(profile);

  const load = () => {
    setState({ status: "loading" });
    getIncomeScenarios(profile)
      .then((data) => {
        setState({ status: "ready", data });
        setSelected(data.scenarios.findIndex((s) => s.annual_income === data.current_annual_income));
      })
      .catch(() => setState({ status: "error" }));
  };
  useEffect(load, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const view = useMemo(() => {
    if (state.status !== "ready" || selected == null) return null;
    const { data } = state;
    const byId = Object.fromEntries(data.programs.map((p) => [p.program_id, p]));
    const currentIndex = data.scenarios.findIndex((s) => s.annual_income === data.current_annual_income);
    const now = data.scenarios[currentIndex];
    const then = data.scenarios[selected];
    const nowIds = new Set(now.matches.map((m) => m.program_id));
    const thenIds = new Set(then.matches.map((m) => m.program_id));
    const byValue = (a, b) => byId[b].monthly_value_usd - byId[a].monthly_value_usd || byId[a].program.localeCompare(byId[b].program);
    // The steepest single-step drop in income plus benefits: the clearest cliff.
    let cliff = null;
    for (let i = 1; i < data.scenarios.length; i++) {
      const drop = yearly(data.scenarios[i - 1]) - yearly(data.scenarios[i]);
      if (drop > 0 && (!cliff || drop > cliff.drop)) cliff = { at: data.scenarios[i].annual_income, drop, index: i };
    }
    // Is the selected income just past a cliff? Compare with one step lower.
    const prev = selected > 0 ? data.scenarios[selected - 1] : null;
    const ended = prev ? prev.matches.map((m) => m.program_id).filter((id) => !thenIds.has(id)) : [];
    const pastCliff = prev && ended.length && yearly(prev) > yearly(then)
      ? { below: prev.annual_income, gain: yearly(prev) - yearly(then), ended }
      : null;
    return {
      data, byId, currentIndex, now, then, cliff, pastCliff,
      lost: [...nowIds].filter((id) => !thenIds.has(id)).sort(byValue),
      gained: [...thenIds].filter((id) => !nowIds.has(id)).sort(byValue),
      incomeDelta: then.annual_income - now.annual_income,
      benefitsDelta: (then.total_estimated_monthly_value - now.total_estimated_monthly_value) * 12,
      totalDelta: yearly(then) - yearly(now),
    };
  }, [state, selected]);

  return (
    <section aria-labelledby="what-if-title" className="mt-8 rounded-lg border border-border p-4 sm:p-6">
      <h2 id="what-if-title" className="text-2xl">What if your income changes?</h2>
      <p className="mt-2 max-w-[70ch]">
        A raise can mean losing a benefit worth more than the raise. Move the slider to see which programs you would gain or
        lose, and what you would have in total each year.
      </p>

      {state.status === "loading" && <p className="mt-4 text-muted" role="status">Checking every program at different incomes…</p>}
      {state.status === "error" && (
        <Alert variant="error" title="We couldn't load this comparison" className="mt-4">
          <p>Check your connection and try again.</p>
          <Button variant="secondary" className="mt-3" onClick={load}>Try again</Button>
        </Alert>
      )}

      {view && (
        <>
          <div className="mt-6">
            <label htmlFor="what-if-income" className="block font-semibold">Yearly household income</label>
            <p className="text-3xl font-extrabold tabular-nums" aria-hidden="true">{usd(view.then.annual_income)}</p>
            <input
              id="what-if-income"
              type="range"
              min={0}
              max={view.data.scenarios.length - 1}
              step={1}
              value={selected}
              onChange={(e) => setSelected(Number(e.target.value))}
              aria-valuetext={`${usd(view.then.annual_income)} a year, ${view.then.pct_fpl}% of the poverty level`}
              className="mt-2 h-11 w-full"
            />
            <div className="flex justify-between text-sm text-muted tabular-nums">
              <span>$0</span>
              <span>{usd(view.data.scenarios[view.data.scenarios.length - 1].annual_income)}</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-3">
              <Button variant="secondary" disabled={selected === view.currentIndex} onClick={() => setSelected(view.currentIndex)}>
                Back to your income ({usd(view.now.annual_income)})
              </Button>
              {view.cliff && (
                <Button variant="secondary" disabled={selected === view.cliff.index} onClick={() => setSelected(view.cliff.index)}>
                  Show me the biggest drop
                </Button>
              )}
            </div>
          </div>

          <div aria-live="polite" className="mt-6">
            {view.incomeDelta === 0 ? (
              <p className="text-lg">
                This is your income now: <strong>{plural(view.now.program_count, "program")}</strong>, about{" "}
                <strong className="tabular-nums">{usd(yearly(view.now))}</strong> a year in income plus estimated benefits.
              </p>
            ) : (
              <dl className="grid gap-4 sm:grid-cols-3">
                {[
                  ["Income", view.incomeDelta],
                  ["Estimated benefits", view.benefitsDelta],
                  ["Total per year", view.totalDelta],
                ].map(([label, v], i) => (
                  <div key={label} className={`rounded-lg p-3 ${i === 2 ? (v < 0 ? "bg-error-bg" : "bg-success-bg") : "bg-surface-alt"}`}>
                    <dt className="text-sm font-semibold">{label}</dt>
                    <dd className={`text-2xl font-extrabold tabular-nums ${i === 2 ? (v < 0 ? "text-error" : "text-success-text") : ""}`}>
                      {signed(v)}<span className="text-base font-semibold">/yr</span>
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            {view.incomeDelta > 0 && view.totalDelta < 0 && (
              <Alert variant="warning" title="This raise could leave you worse off" className="mt-4">
                <p>
                  Earning {usd(view.incomeDelta)} more a year could cost about {usd(-view.benefitsDelta)} in benefits, leaving you
                  roughly {usd(-view.totalDelta)} a year behind where you are now. This is called a benefits cliff. A caseworker
                  can tell you about transition rules that soften it for some programs.
                </p>
              </Alert>
            )}
            {view.pastCliff && (
              <Alert variant="warning" title="You're just past a benefits cliff" className="mt-4">
                <p>
                  At {usd(view.pastCliff.below)} a year you would have about {usd(view.pastCliff.gain)} more in total, because{" "}
                  {view.pastCliff.ended.map((id) => view.byId[id].program).join(", ")}{" "}
                  {view.pastCliff.ended.length === 1 ? "ends" : "end"} right here.
                </p>
              </Alert>
            )}
            {view.incomeDelta !== 0 && (
              <div className="mt-5 grid gap-6 sm:grid-cols-2">
                <ProgramList title={`You would no longer qualify (${view.lost.length})`} ids={view.lost} byId={view.byId} tone="text-error" />
                <ProgramList title={`You would newly qualify (${view.gained.length})`} ids={view.gained} byId={view.byId} tone="text-success-text" />
                {!view.lost.length && !view.gained.length && <p>The same programs fit at this income.</p>}
              </div>
            )}
          </div>

          <h3 className="mt-8 text-lg">Estimated benefits per year at each income</h3>
          <p className="text-sm text-muted">Each drop is a program's income limit. Tap or click the chart to move the slider there.</p>
          <Chart scenarios={view.data.scenarios} currentIndex={view.currentIndex} selected={selected} onSelect={setSelected} />
          {view.cliff && (
            <p className="mt-3 text-sm">
              Biggest drop: going past about <strong className="tabular-nums">{usd(view.cliff.at)}</strong> leaves you about{" "}
              <strong className="tabular-nums">{usd(view.cliff.drop)}</strong> a year worse off, even counting the extra pay.
            </p>
          )}

          <details className="mt-4">
            <summary className="font-semibold text-primary underline">Show these numbers as a table</summary>
            <div className="mt-3 max-h-80 overflow-auto rounded border border-border">
              <table className="w-full text-sm tabular-nums">
                <thead className="sticky top-0 bg-surface-alt text-left">
                  <tr><th className="p-2">Income</th><th className="p-2">% of poverty level</th><th className="p-2">Programs</th><th className="p-2">Est. benefits/yr</th><th className="p-2">Total/yr</th></tr>
                </thead>
                <tbody>
                  {view.data.scenarios.map((s, i) => (
                    <tr key={s.annual_income} className={i === view.currentIndex ? "bg-primary-lighter font-semibold" : "border-t border-divider"}>
                      <td className="p-2">{usd(s.annual_income)}{i === view.currentIndex && " (now)"}</td>
                      <td className="p-2">{s.pct_fpl}%</td>
                      <td className="p-2">{s.program_count}</td>
                      <td className="p-2">{usd(s.total_estimated_monthly_value * 12)}</td>
                      <td className="p-2">{usd(yearly(s))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          <p className="mt-4 max-w-[75ch] text-sm text-muted">
            Uses the same program rules as your matches, with every other answer kept the same. Benefit amounts are estimates
            and health coverage has no dollar value, so the totals only count cash, food, utility and similar help. Taxes and
            work costs are not included.
          </p>
        </>
      )}
    </section>
  );
}
