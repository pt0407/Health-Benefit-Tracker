// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 7.
// Receives the MatchResponse (backend/models/match_result.py) via router state.
// Dollar values are estimates, labeled as Person 3 chose (see PR #18).

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Icon from "../shared/Icon.jsx";
import ActionPlan from "./ActionPlan.jsx";

// Match strength is shown as text plus a three-step meter, never color alone.
const MATCH = {
  high: { label: "Strong match", steps: 3, tone: "text-good-800", fill: "bg-good-800" },
  medium: { label: "Possible match", steps: 2, tone: "text-brand-700", fill: "bg-brand-700" },
  low: { label: "Worth checking", steps: 1, tone: "text-subtle", fill: "bg-subtle" },
};
const ORDER = { high: 0, medium: 1, low: 2 };

const usd = (v) => `$${Math.round(v).toLocaleString()}`;
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function MatchMeter({ confidence }) {
  const m = MATCH[confidence] || MATCH.low;
  return (
    <span className={`inline-flex items-center gap-2 text-sm font-semibold ${m.tone}`}>
      <span className="flex gap-0.5" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <span key={i} className={`h-3 w-1.5 rounded-sm ${i <= m.steps ? m.fill : "bg-line"}`} />
        ))}
      </span>
      {m.label}
    </span>
  );
}

function ProgramCard({ program }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-2xl border border-line bg-surface p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <h2 className="text-xl font-bold text-ink">{program.program}</h2>
        <div className="shrink-0 sm:pt-1"><MatchMeter confidence={program.confidence} /></div>
      </div>
      <p className="mt-3 max-w-[65ch] text-muted">{program.reason}</p>

      {(program.monthly_value_usd > 0 || program.processing_time) && (
        <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {program.monthly_value_usd > 0 && (
            <div className="flex gap-1.5">
              <dt className="text-muted">Est. value</dt>
              <dd className="font-semibold text-ink tabular-nums">{usd(program.monthly_value_usd)}/mo</dd>
            </div>
          )}
          {program.processing_time && (
            <div className="flex gap-1.5">
              <dt className="text-muted">Processing</dt>
              <dd className="font-semibold text-ink">{program.processing_time}</dd>
            </div>
          )}
        </dl>
      )}

      <div className="mt-5 flex flex-wrap gap-2.5">
        {program.application_url && (
          <a
            href={program.application_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-700 px-4 font-semibold text-white transition-colors hover:bg-brand-800"
          >
            Apply
            <Icon name="external" className="h-4 w-4" />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        )}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 font-semibold text-brand-800 transition-colors hover:border-brand-700 hover:bg-brand-50"
        >
          See how to apply
        </button>
      </div>
      {open && <ActionPlan program={program} onClose={() => setOpen(false)} />}

      {(program.tip || program.source) && (
        <div className="mt-5 space-y-1 border-t border-line pt-4 text-sm">
          {program.tip && <p className="text-muted">{program.tip}</p>}
          {program.source && <p className="text-subtle">Source: {program.source}</p>}
        </div>
      )}
    </li>
  );
}

function ValueChart({ programs }) {
  const data = programs.map((p) => ({
    name: p.program.length > 24 ? `${p.program.slice(0, 23)}…` : p.program,
    full: p.program,
    value: p.monthly_value_usd,
  }));
  return (
    <figure className="mt-8 rounded-2xl border border-line bg-surface p-5 sm:p-6">
      <figcaption className="font-semibold text-ink">Estimated monthly value by program</figcaption>
      <div className="mt-4" style={{ height: 48 * data.length + 32 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid horizontal={false} stroke="#d6dde8" />
            <XAxis type="number" tickFormatter={(v) => `$${v}`} tick={{ fontSize: 12, fill: "#475569" }} stroke="#9aa8bd" />
            <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12, fill: "#0f172a" }} stroke="#9aa8bd" />
            <Tooltip
              cursor={{ fill: "#eef3fd" }}
              labelFormatter={(_, payload) => payload?.[0]?.payload.full}
              formatter={(v) => [`${usd(v)}/mo`, "Estimated value"]}
              contentStyle={{ borderRadius: 12, borderColor: "#d6dde8", fontFamily: "inherit" }}
            />
            <Bar dataKey="value" fill="#1e40af" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export default function ResultsDashboard() {
  const result = useLocation().state;
  if (!result) {
    return (
      <main className="mx-auto max-w-xl px-4 pt-16 pb-20 sm:px-6">
        <h1 className="text-3xl font-bold text-brand-900">No results yet</h1>
        <p className="mt-3 text-lg text-muted">
          Answer the 10 questions first, and we'll show the programs your household may qualify for.
        </p>
        <Link
          to="/quiz"
          className="mt-8 inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-700 px-6 text-lg font-semibold text-white transition-colors hover:bg-brand-800"
        >
          Start the questions
          <Icon name="arrowRight" />
        </Link>
      </main>
    );
  }

  const programs = [...result.matched_programs].sort(
    (a, b) => (ORDER[a.confidence] ?? 3) - (ORDER[b.confidence] ?? 3),
  );
  const valued = programs.filter((p) => p.monthly_value_usd > 0);
  const count = result.program_count;

  return (
    <main className="mx-auto max-w-3xl px-4 pt-10 pb-20 sm:px-6 sm:pt-14">
      <h1 className="text-3xl font-bold text-brand-900 sm:text-4xl">
        {count === 0
          ? "We didn't find a clear match"
          : `${plural(count, "program")} may fit your household`}
      </h1>
      {count > 0 && (
        <p className="mt-3 max-w-[60ch] text-lg text-muted">
          {result.total_estimated_annual_value > 0 ? (
            <>
              You may qualify for up to an estimated{" "}
              <strong className="font-bold text-ink tabular-nums">{usd(result.total_estimated_annual_value)}/year</strong>{" "}
              (about <span className="tabular-nums">{usd(result.total_estimated_monthly_value)}</span>/mo).
              Health coverage and other non-cash programs aren't counted in that total.
            </>
          ) : (
            "Health coverage and other non-cash programs don't have a dollar total."
          )}{" "}
          Strongest matches are listed first.
        </p>
      )}

      {result.warnings?.length > 0 && (
        <section
          aria-labelledby="warnings-title"
          className="mt-8 rounded-2xl border border-warn-500/40 bg-warn-50 p-5 text-warn-900"
        >
          <h2 id="warnings-title" className="flex items-center gap-2 font-bold">
            <Icon name="alert" className="h-5 w-5 text-warn-500" />
            Worth knowing
          </h2>
          <ul className="mt-2 space-y-2 pl-7">
            {result.warnings.map((w) => (
              <li key={w} className="max-w-[65ch]">{w}</li>
            ))}
          </ul>
        </section>
      )}

      {valued.length > 0 && <ValueChart programs={valued} />}

      {count > 0 && (
        <ul className="mt-8 space-y-4">
          {programs.map((p) => (
            <ProgramCard key={p.program_id || p.program} program={p} />
          ))}
        </ul>
      )}

      {count === 0 && (
        <p className="mt-4 max-w-[60ch] text-lg text-muted">
          Program rules change, so it's still worth checking{" "}
          <a href="https://www.usa.gov/benefits" target="_blank" rel="noreferrer" className="font-semibold text-brand-700 underline">
            USA.gov's benefit finder
          </a>{" "}
          directly.
        </p>
      )}

      {valued.length > 0 && (
        <p className="mt-10 max-w-[70ch] text-sm text-subtle">
          Dollar amounts are estimates based on program averages and your answers. They are not
          a guarantee of benefits. Actual amounts depend on your full application and caseworker
          review.
        </p>
      )}

      <div className="mt-10 border-t border-line pt-6">
        <Link to="/quiz" className="inline-flex min-h-11 items-center gap-2 font-semibold text-brand-700 underline">
          <Icon name="arrowLeft" className="h-4 w-4" />
          Start over with different answers
        </Link>
      </div>
    </main>
  );
}
