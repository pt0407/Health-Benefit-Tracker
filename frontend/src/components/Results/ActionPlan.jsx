// Owner: Person 4. See docs/BUILD_PLAN.md §3 Component 6.
// Step-by-step "how to apply" plan for one MatchedProgram
// (backend/models/match_result.py). The steps come from the backend; this
// component only lays them out: documents first, then the steps in order.

import { useEffect, useRef, useState } from "react";

function stepsFor(program) {
  if (program.next_steps?.length) return program.next_steps;
  // Results without generated steps (e.g. from the insurance agent) still get a plan.
  const steps = [];
  if (program.next_step) steps.push({ step: 1, action: program.next_step });
  if (program.application_url && !program.next_step?.includes(program.application_url)) {
    steps.push({ step: steps.length + 1, action: "Apply online", url: program.application_url });
  }
  return steps;
}

export default function ActionPlan({ program, onClose }) {
  const dialogRef = useRef(null);
  const steps = stepsFor(program);
  const documents = steps.flatMap((s) => s.documents || []);
  const actions = steps.filter((s) => !s.documents?.length);
  const [checked, setChecked] = useState({});

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4 print:static print:bg-white"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-plan-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-6 shadow-xl outline-none sm:rounded-2xl print:max-h-none print:shadow-none"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Your action plan</p>
            <h2 id="action-plan-title" className="mt-1 text-xl font-bold">{program.program}</h2>
            {program.monthly_value_usd > 0 && (
              <p className="mt-1 text-sm font-medium text-green-700">
                Est. ${Math.round(program.monthly_value_usd).toLocaleString()}/mo
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close action plan"
            className="rounded-lg px-2 py-1 text-2xl leading-none text-gray-400 hover:bg-gray-100 hover:text-gray-700 print:hidden"
          >
            ×
          </button>
        </div>

        {documents.length > 0 && (
          <section className="mt-6">
            <h3 className="font-semibold">Before you start, gather these</h3>
            <ul className="mt-2 space-y-2">
              {documents.map((doc) => (
                <li key={doc}>
                  <label className="flex cursor-pointer items-start gap-3 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={!!checked[doc]}
                      onChange={() => setChecked((c) => ({ ...c, [doc]: !c[doc] }))}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-blue-600"
                    />
                    <span className={checked[doc] ? "text-gray-400 line-through" : ""}>{doc}</span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        )}

        {actions.length > 0 && (
          <section className="mt-6">
            <h3 className="font-semibold">Steps</h3>
            <ol className="mt-2 space-y-3">
              {actions.map((s, i) => (
                <li key={`${s.step}-${s.action}`} className="flex gap-3 text-sm">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <div className="text-gray-700">
                    <p className="font-medium text-gray-900">
                      {s.action}
                      {s.time_required && <span className="font-normal text-gray-500"> · {s.time_required}</span>}
                    </p>
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noreferrer" className="break-all text-blue-600 underline">
                        {s.url.replace(/^https?:\/\//, "")}
                      </a>
                    )}
                    {s.note && <p className="text-gray-500">{s.note}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}

        {program.processing_time && (
          <p className="mt-6 text-sm text-gray-600">
            <span className="font-medium">Processing time:</span> {program.processing_time}
          </p>
        )}
        {program.tip && (
          <p className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-900">{program.tip}</p>
        )}
        {program.source && <p className="mt-4 text-xs text-gray-400">Source: {program.source}</p>}

        <div className="mt-6 flex flex-wrap gap-2 print:hidden">
          {program.application_url && (
            <a
              href={program.application_url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Apply now
            </a>
          )}
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            Print this plan
          </button>
        </div>
      </div>
    </div>
  );
}
