// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 7.
// Receives the MatchResponse (backend/models/match_result.py) via router state.
// Dollar values are estimates — labeled as such per CLAUDE.md Person 2 guidance.

import { useLocation, useNavigate } from "react-router-dom";

const CONFIDENCE_LABEL = {
  high: { text: "Likely eligible", className: "bg-green-100 text-green-800" },
  medium: { text: "May be eligible", className: "bg-yellow-100 text-yellow-800" },
  low: { text: "Check eligibility", className: "bg-gray-100 text-gray-700" },
};

function ConfidenceBadge({ confidence }) {
  const { text, className } = CONFIDENCE_LABEL[confidence] ?? CONFIDENCE_LABEL.low;
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {text}
    </span>
  );
}

function ProgramCard({ program }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <h3 className="font-semibold text-gray-900">{program.program}</h3>
        <ConfidenceBadge confidence={program.confidence} />
      </div>

      <p className="mt-2 text-sm text-gray-600">{program.reason}</p>

      {program.monthly_value_usd > 0 && (
        <p className="mt-3 text-sm font-medium text-gray-800">
          Est.{" "}
          <span className="text-blue-700">
            ${program.monthly_value_usd.toLocaleString()}/mo
          </span>
        </p>
      )}

      {program.processing_time && (
        <p className="mt-1 text-xs text-gray-500">
          Processing time: {program.processing_time}
        </p>
      )}

      {program.tip && (
        <p className="mt-2 text-xs text-gray-500 italic">{program.tip}</p>
      )}

      {program.next_step && (
        <div className="mt-4">
          <p className="text-xs font-medium text-gray-700 uppercase tracking-wide mb-1">
            Next step
          </p>
          {program.application_url ? (
            <a
              href={program.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 underline hover:text-blue-800"
            >
              {program.next_step}
            </a>
          ) : (
            <p className="text-sm text-gray-700">{program.next_step}</p>
          )}
        </div>
      )}
    </div>
  );
}

function WarningBanner({ warnings }) {
  if (!warnings?.length) return null;
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-1">
      {warnings.map((w, i) => (
        <p key={i} className="text-sm text-amber-800">
          ⚠ {w}
        </p>
      ))}
    </div>
  );
}

export default function ResultsDashboard() {
  const result = useLocation().state;
  const navigate = useNavigate();

  if (!result) {
    return (
      <main className="mx-auto max-w-xl px-4 py-16 text-center">
        <h2 className="text-2xl font-bold">No results yet</h2>
        <p className="mt-2 text-gray-600">Take the quiz to see which benefits you may qualify for.</p>
        <button
          onClick={() => navigate("/quiz")}
          className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
        >
          Start the quiz
        </button>
      </main>
    );
  }

  const {
    matched_programs = [],
    total_estimated_annual_value = 0,
    total_estimated_monthly_value = 0,
    program_count = 0,
    warnings = [],
  } = result;

  return (
    <main className="mx-auto max-w-xl px-4 py-12 space-y-6">
      {/* Header summary */}
      <div className="rounded-xl bg-blue-600 px-6 py-8 text-white text-center">
        <p className="text-sm font-medium uppercase tracking-wide opacity-80 mb-1">
          You may qualify for up to an estimated
        </p>
        <p className="text-5xl font-bold">
          ${total_estimated_annual_value.toLocaleString()}
          <span className="text-2xl font-normal opacity-80">/year</span>
        </p>
        <p className="mt-1 text-sm opacity-70">
          (~${total_estimated_monthly_value.toLocaleString()}/mo) across {program_count}{" "}
          {program_count === 1 ? "program" : "programs"}
        </p>
      </div>

      {/* Warnings */}
      <WarningBanner warnings={warnings} />

      {/* Program cards */}
      {matched_programs.length > 0 ? (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Programs matched</h2>
          {matched_programs.map((p, i) => (
            <ProgramCard key={p.program_id ?? i} program={p} />
          ))}
        </div>
      ) : (
        <p className="text-gray-600 text-sm">No programs matched your profile.</p>
      )}

      {/* Estimate disclosure */}
      <p className="text-xs text-gray-400 leading-relaxed">
        Dollar amounts are estimates based on program averages and your answers. They are not
        a guarantee of benefits. Actual amounts depend on your full application and caseworker
        review.
      </p>

      {/* Retake */}
      <button
        onClick={() => navigate("/quiz")}
        className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Retake quiz
      </button>
    </main>
  );
}
