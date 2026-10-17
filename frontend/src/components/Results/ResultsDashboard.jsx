// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 7.
// Receives the MatchResponse (backend/models/match_result.py) via router state.
// Dollar values are estimates, labeled as Person 3 chose (see PR #18).

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon from "../shared/Icon.jsx";
import ActionPlan from "./ActionPlan.jsx";
import { exportWorksheetPdf } from "../../api/benefitsApi.js";

// Programs are grouped by match strength; the meter repeats it as shape, not color alone.
const GROUPS = [
  { key: "high", title: "Strong matches", blurb: "Your answers meet every rule we can check.", steps: 3 },
  { key: "medium", title: "Possible matches", blurb: "Depends on something the questions don't cover, like savings or each person's situation.", steps: 2 },
  { key: "low", title: "Worth checking", blurb: "Less likely, but rules have exceptions. Applying is free.", steps: 1 },
];

// Segment colors for the value breakdown, each paired with a labeled legend row.
const SEGMENTS = ["bg-accent", "bg-brand-200", "bg-cream", "bg-accent-600", "bg-on-brand-muted"];

const usd = (v) => `$${Math.round(v).toLocaleString()}`;
const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;

function Meter({ steps, onDark = false }) {
  return (
    <span className="flex gap-1" aria-hidden="true">
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className={`h-4 w-2 rounded-sm ${i <= steps ? (onDark ? "bg-accent" : "bg-brand-700") : onDark ? "bg-brand-800" : "bg-line"}`}
        />
      ))}
    </span>
  );
}

function ProgramCard({ program }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="flex flex-col rounded-3xl bg-surface p-6 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <h3 className="max-w-[28ch] text-xl font-bold text-ink">{program.program}</h3>
        {program.monthly_value_usd > 0 ? (
          <span className="rounded-full bg-accent-100 px-3 py-1 text-sm font-bold text-warn-900 tabular-nums">
            Est. {usd(program.monthly_value_usd)}/mo
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-muted">{program.reason}</p>
      {program.processing_time && (
        <p className="mt-3 flex items-center gap-2 text-sm text-muted">
          <Icon name="clock" className="h-4 w-4 text-brand-700" />
          Processing time: <span className="font-semibold text-ink">{program.processing_time}</span>
        </p>
      )}

      <div className="mt-auto pt-5">
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-900 px-4 font-semibold text-cream transition hover:bg-brand-800"
          >
            <Icon name="list" className="h-4 w-4" />
            How to apply
          </button>
          {program.application_url && (
            <a
              href={program.application_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-line px-4 font-semibold text-brand-900 transition-colors hover:border-brand-700 hover:bg-brand-50"
            >
              Apply online
              <Icon name="external" className="h-4 w-4" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          )}
        </div>
        {program.source && <p className="mt-4 text-sm text-subtle">Source: {program.source}</p>}
      </div>
      {open && <ActionPlan program={program} onClose={() => setOpen(false)} />}
    </li>
  );
}

function Summary({ result }) {
  const count = result.program_count;
  const valued = result.matched_programs
    .filter((p) => p.monthly_value_usd > 0)
    .sort((a, b) => b.monthly_value_usd - a.monthly_value_usd);
  const monthly = valued.reduce((sum, p) => sum + p.monthly_value_usd, 0);
  const strong = result.matched_programs.filter((p) => p.confidence === "high").length;

  return (
    <section className="on-brand overflow-hidden rounded-[2rem] bg-brand-900 text-cream">
      <div className="p-7 sm:p-10">
        <h1 className="font-display max-w-[18ch] text-4xl font-semibold sm:text-6xl">
          {plural(count, "program")} may fit your household.
        </h1>
        <div className="mt-6 grid grid-cols-1 gap-10 lg:grid-cols-2 lg:items-start">
          <div>
            {result.total_estimated_annual_value > 0 ? (
              <p className="max-w-[48ch] text-lg text-on-brand-muted">
                You may qualify for up to an estimated{" "}
                <strong className="font-bold text-cream tabular-nums">{usd(result.total_estimated_annual_value)}/year</strong>{" "}
                (about <span className="tabular-nums">{usd(result.total_estimated_monthly_value)}</span>/mo).
                Health coverage isn't counted in that total.
              </p>
            ) : (
              <p className="max-w-[48ch] text-lg text-on-brand-muted">
                Health coverage and other non-cash programs don't have a dollar total.
              </p>
            )}
            {strong > 0 && (
              <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-accent px-4 py-1.5 font-semibold text-brand-950">
                <Icon name="check" className="h-4 w-4" />
                {plural(strong, "strong match", "strong matches")}
              </p>
            )}
          </div>

          {valued.length > 0 && (
            <figure className="min-w-0">
              <figcaption className="text-sm font-semibold text-on-brand-muted">Where the estimate comes from</figcaption>
              <div className="mt-3 flex h-4 gap-1 overflow-hidden rounded-full" aria-hidden="true">
                {valued.map((p, i) => (
                  <span
                    key={p.program}
                    className={`${SEGMENTS[i % SEGMENTS.length]} first:rounded-l-full last:rounded-r-full`}
                    style={{ width: `${(p.monthly_value_usd / monthly) * 100}%` }}
                  />
                ))}
              </div>
              <ul className="mt-4 space-y-2">
                {valued.map((p, i) => (
                  <li key={p.program} className="flex items-center gap-3 text-sm">
                    <span className={`h-3 w-3 shrink-0 rounded-sm ${SEGMENTS[i % SEGMENTS.length]}`} aria-hidden="true" />
                    <span className="min-w-0 flex-1">{p.program}</span>
                    <span className="shrink-0 font-semibold tabular-nums">Est. {usd(p.monthly_value_usd)}/mo</span>
                  </li>
                ))}
              </ul>
            </figure>
          )}
        </div>
      </div>
    </section>
  );
}

export default function ResultsDashboard() {
  const state = useLocation().state;
  const result = state?.result ?? state; // tolerate bare MatchResponse state
  const profile = state?.profile;
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  async function downloadPdf() {
    setExporting(true);
    setExportError(null);
    try {
      await exportWorksheetPdf(profile, result);
    } catch {
      setExportError("Couldn't generate the PDF. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  if (!result) {
    return (
      <main className="mx-auto max-w-2xl px-4 pt-16 pb-24 sm:px-6 sm:pt-24">
        <h1 className="font-display text-5xl font-semibold text-brand-900">No results yet.</h1>
        <p className="mt-4 text-lg text-muted">
          Answer the 10 questions first, and we'll show the programs your household may qualify for.
        </p>
        <Link
          to="/quiz"
          className="mt-9 inline-flex min-h-14 items-center gap-2 rounded-2xl bg-brand-900 px-7 text-lg font-semibold text-cream transition hover:bg-brand-800"
        >
          Start the questions
          <Icon name="arrowRight" />
        </Link>
      </main>
    );
  }

  const count = result.program_count;
  const hasValues = result.matched_programs.some((p) => p.monthly_value_usd > 0);

  return (
    <main className="mx-auto max-w-6xl px-4 pt-6 pb-20 sm:px-6 sm:pt-10">
      {count > 0 ? (
        <Summary result={result} />
      ) : (
        <section className="rounded-[2rem] bg-surface p-8 shadow-[var(--shadow-card)] sm:p-10">
          <h1 className="font-display text-4xl font-semibold text-brand-900">We didn't find a clear match.</h1>
          <p className="mt-4 max-w-[60ch] text-lg text-muted">
            Program rules change and have exceptions, so it's still worth checking{" "}
            <a href="https://www.usa.gov/benefits" target="_blank" rel="noreferrer" className="font-semibold text-brand-700 underline">
              USA.gov's benefit finder
            </a>{" "}
            directly.
          </p>
        </section>
      )}

      {result.warnings?.length > 0 && (
        <section aria-labelledby="warnings-title" className="mt-6 flex gap-4 rounded-3xl bg-warn-50 p-6 text-warn-900">
          <Icon name="alert" className="mt-0.5 h-6 w-6 text-warn-500" />
          <div>
            <h2 id="warnings-title" className="text-lg font-bold">Worth knowing</h2>
            <ul className="mt-1 space-y-1.5">
              {result.warnings.map((w) => (
                <li key={w} className="max-w-[75ch]">{w}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {GROUPS.map((g) => {
        const programs = result.matched_programs.filter((p) => p.confidence === g.key);
        if (!programs.length) return null;
        return (
          <section key={g.key} aria-labelledby={`group-${g.key}`} className="mt-14">
            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b border-line pb-4">
              <div>
                <h2 id={`group-${g.key}`} className="font-display flex items-center gap-3 text-3xl font-semibold text-brand-900">
                  <Meter steps={g.steps} />
                  {g.title}
                  <span className="font-sans text-lg font-semibold text-muted tabular-nums">{programs.length}</span>
                </h2>
                <p className="mt-1 text-muted">{g.blurb}</p>
              </div>
            </div>
            <ul className="mt-6 grid gap-5 md:grid-cols-2">
              {programs.map((p) => (
                <ProgramCard key={p.program_id || p.program} program={p} />
              ))}
            </ul>
          </section>
        );
      })}

      {hasValues && (
        <p className="mt-14 max-w-[70ch] text-sm text-subtle">
          Dollar amounts are estimates based on program averages and your answers. They are not
          a guarantee of benefits. Actual amounts depend on your full application and caseworker
          review.
        </p>
      )}

      {exportError && <p className="mt-6 text-sm text-red-600">{exportError}</p>}

      <div className="mt-10 flex flex-wrap items-center gap-4 border-t border-line pt-8">
        <Link
          to="/quiz"
          className="inline-flex min-h-12 items-center gap-2 rounded-2xl border-2 border-line px-5 font-semibold text-brand-900 transition-colors hover:border-brand-700 hover:bg-brand-50"
        >
          <Icon name="pencil" className="h-4 w-4" />
          Start over with different answers
        </Link>
        {profile && (
          <button
            type="button"
            onClick={downloadPdf}
            disabled={exporting}
            className="inline-flex min-h-12 items-center gap-2 rounded-2xl bg-brand-900 px-5 font-semibold text-cream transition hover:bg-brand-800 disabled:opacity-40"
          >
            <Icon name="printer" className="h-4 w-4" />
            {exporting ? "Preparing…" : "Download worksheet (PDF)"}
          </button>
        )}
      </div>
    </main>
  );
}
