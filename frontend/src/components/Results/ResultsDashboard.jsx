// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 7.
// Receives the MatchResponse (backend/models/match_result.py) via router state.
// Dollar values are estimates, labeled as Person 3 chose (see PR #18).

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ActionPlan from "./ActionPlan.jsx";

const CONFIDENCE_STYLES = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-200 text-gray-700",
};

function ProgramCard({ program }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">{program.program}</h3>
          {program.monthly_value_usd > 0 && (
            <p className="text-green-700 font-medium">Est. ${Math.round(program.monthly_value_usd).toLocaleString()}/mo</p>
          )}
        </div>
        <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold capitalize ${CONFIDENCE_STYLES[program.confidence] || CONFIDENCE_STYLES.low}`}>
          {program.confidence}
        </span>
      </div>
      <p className="mt-2 text-sm text-gray-600">{program.reason}</p>
      {program.processing_time && (
        <p className="mt-1 text-xs text-gray-500">Processing: {program.processing_time}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {program.application_url && (
          <a
            href={program.application_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Apply
          </a>
        )}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
        >
          Action plan
        </button>
      </div>
      {open && <ActionPlan program={program} onClose={() => setOpen(false)} />}
      {program.tip && <p className="mt-3 text-xs italic text-gray-500">{program.tip}</p>}
      {program.source && <p className="mt-1 text-xs text-gray-400">Source: {program.source}</p>}
    </div>
  );
}

export default function ResultsDashboard() {
  const result = useLocation().state;
  if (!result) {
    return (
      <main className="mx-auto max-w-xl px-4 py-16 text-center">
        <h2 className="text-2xl font-bold">Results</h2>
        <p className="mt-2 text-gray-600">Take the quiz to see your results.</p>
        <Link to="/quiz" className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700">
          Start the quiz
        </Link>
      </main>
    );
  }

  const valued = result.matched_programs.filter((p) => p.monthly_value_usd > 0);

  return (
    <main className="mx-auto max-w-2xl px-4 py-12">
      <div className="rounded-2xl bg-blue-600 p-8 text-center text-white">
        {result.total_estimated_annual_value > 0 ? (
          <>
            <p className="text-lg opacity-90">You may qualify for up to an estimated</p>
            <p className="mt-1 text-4xl font-bold">
              ${Math.round(result.total_estimated_annual_value).toLocaleString()}/year
            </p>
            <p className="mt-1 opacity-90">
              (~${Math.round(result.total_estimated_monthly_value).toLocaleString()}/mo) across {result.program_count} program{result.program_count === 1 ? "" : "s"}
            </p>
          </>
        ) : (
          <>
            <p className="text-2xl font-bold">{result.program_count} program{result.program_count === 1 ? "" : "s"} may fit your household</p>
            <p className="mt-1 opacity-90">Health coverage and other non-cash programs don't have a dollar total.</p>
          </>
        )}
      </div>

      {result.warnings?.length > 0 && (
        <div className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4">
          {result.warnings.map((w) => (
            <p key={w} className="text-sm text-amber-900">⚠ {w}</p>
          ))}
        </div>
      )}

      {valued.length > 0 && (
        <div className="mt-8 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={valued} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="program" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis tickFormatter={(v) => `$${v}`} width={60} />
              <Tooltip formatter={(v) => [`$${Math.round(v).toLocaleString()}/mo`, "Estimated value"]} />
              <Bar dataKey="monthly_value_usd" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-8 space-y-4">
        {result.matched_programs.map((p) => (
          <ProgramCard key={p.program_id || p.program} program={p} />
        ))}
      </div>

      {result.program_count === 0 && (
        <p className="mt-8 text-center text-gray-600">
          We didn't find a clear match — but program rules change, so it's still worth checking{" "}
          <a href="https://www.usa.gov/benefits" target="_blank" rel="noreferrer" className="text-blue-600 underline">USA.gov</a> directly.
        </p>
      )}

      {valued.length > 0 && (
        <p className="mt-8 text-xs leading-relaxed text-gray-400">
          Dollar amounts are estimates based on program averages and your answers. They are not
          a guarantee of benefits. Actual amounts depend on your full application and caseworker
          review.
        </p>
      )}

      <div className="mt-10 text-center">
        <Link to="/quiz" className="text-blue-600 underline">Start over</Link>
      </div>
    </main>
  );
}
