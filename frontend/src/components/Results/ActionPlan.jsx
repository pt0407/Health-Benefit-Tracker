// Owner: Person 4. See docs/BUILD_PLAN.md §3 Component 6.
// Step-by-step "how to apply" plan for one MatchedProgram
// (backend/models/match_result.py). The steps come from the backend; this
// component only lays them out: documents first, then the steps in order.

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Icon from "../shared/Icon.jsx";

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

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

export default function ActionPlan({ program, onClose }) {
  const dialogRef = useRef(null);
  const steps = stepsFor(program);
  const documents = steps.flatMap((s) => s.documents || []);
  const actions = steps.filter((s) => !s.documents?.length);
  const [checked, setChecked] = useState({});
  const done = documents.filter((d) => checked[d]).length;

  useEffect(() => {
    const opener = document.activeElement;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      // Keep Tab inside the dialog while it is open.
      if (e.key === "Tab" && dialogRef.current) {
        const items = [...dialogRef.current.querySelectorAll(FOCUSABLE)];
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.classList.add("overflow-hidden", "printing-plan");
    dialogRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("overflow-hidden", "printing-plan");
      opener?.focus?.();
    };
  }, [onClose]);

  return createPortal(
    <div
      className="action-plan fixed inset-0 z-50 flex items-end justify-center bg-brand-900/50 sm:items-center sm:p-4 print:static print:block print:bg-white"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-plan-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-surface p-6 shadow-[0_24px_48px_-12px_rgb(15_42_95/0.35)] outline-none sm:rounded-2xl sm:p-7 print:max-h-none print:max-w-none print:shadow-none"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="action-plan-title" className="text-2xl font-bold text-brand-900">
              How to apply: {program.program}
            </h2>
            {program.monthly_value_usd > 0 && (
              <p className="mt-1 text-sm font-semibold text-good-800 tabular-nums">
                Est. ${Math.round(program.monthly_value_usd).toLocaleString()}/mo
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-mt-1 -mr-2 flex h-11 w-11 items-center justify-center rounded-xl text-muted transition-colors hover:bg-brand-50 hover:text-brand-900 print:hidden"
          >
            <Icon name="close" />
          </button>
        </div>

        {documents.length > 0 && (
          <section className="mt-6">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-bold text-ink">Gather these first</h3>
              <p className="text-sm text-muted tabular-nums" aria-live="polite">
                {done} of {documents.length} ready
              </p>
            </div>
            <ul className="mt-2 divide-y divide-line rounded-xl border border-line">
              {documents.map((doc) => (
                <li key={doc}>
                  <label className="flex min-h-12 items-start gap-3 px-3 py-3 text-ink transition-colors hover:bg-brand-50/60">
                    <input
                      type="checkbox"
                      checked={!!checked[doc]}
                      onChange={() => setChecked((c) => ({ ...c, [doc]: !c[doc] }))}
                      className="mt-1 h-4.5 w-4.5 shrink-0"
                    />
                    <span className={checked[doc] ? "text-subtle line-through" : ""}>{doc}</span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        )}

        {actions.length > 0 && (
          <section className="mt-7">
            <h3 className="font-bold text-ink">Then follow these steps</h3>
            <ol className="mt-3 space-y-4">
              {actions.map((s, i) => (
                <li key={`${s.step}-${s.action}`} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-700 text-sm font-bold text-white tabular-nums">
                    {i + 1}
                  </span>
                  <div className="pt-0.5">
                    <p className="font-semibold text-ink">
                      {s.action}
                      {s.time_required && <span className="font-normal text-muted"> · {s.time_required}</span>}
                    </p>
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noreferrer" className="break-all text-brand-700 underline">
                        {s.url.replace(/^https?:\/\//, "")}
                      </a>
                    )}
                    {s.note && <p className="mt-0.5 text-muted">{s.note}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}

        {program.processing_time && (
          <p className="mt-7 flex items-center gap-2 text-muted">
            <Icon name="clock" className="h-5 w-5 text-brand-700" />
            <span><span className="font-semibold text-ink">Processing time:</span> {program.processing_time}</span>
          </p>
        )}
        {program.tip && (
          <p className="mt-4 rounded-xl bg-brand-50 p-4 text-brand-900">{program.tip}</p>
        )}
        {program.source && <p className="mt-4 text-sm text-subtle">Source: {program.source}</p>}

        <div className="mt-7 flex flex-wrap gap-2.5 print:hidden">
          {program.application_url && (
            <a
              href={program.application_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-700 px-4 font-semibold text-white transition-colors hover:bg-brand-800"
            >
              Apply now
              <Icon name="external" className="h-4 w-4" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          )}
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line-strong px-4 font-semibold text-brand-800 transition-colors hover:border-brand-700 hover:bg-brand-50"
          >
            <Icon name="printer" className="h-4 w-4" />
            Print this plan
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
