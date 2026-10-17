// Owner: Person 4 (restyled for Civis, logic unchanged). See docs/BUILD_PLAN.md section 3, Component 6.
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
      className="action-plan fixed inset-0 z-50 flex items-end justify-center bg-primary-dark/70 sm:items-center sm:p-4 print:static print:block print:bg-white"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-plan-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92dvh] w-full max-w-lg overflow-y-auto border-t-8 border-primary-dark bg-white p-6 outline-none sm:p-8 print:max-h-none print:max-w-none"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="action-plan-title" className="text-2xl">{program.program}</h2>
            <p className="mt-1 text-muted">Your step-by-step plan to apply</p>
            {program.monthly_value_usd > 0 && (
              <p className="mt-2 font-bold tabular-nums">Est. ${Math.round(program.monthly_value_usd).toLocaleString()}/mo</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-mt-2 -mr-2 flex h-11 w-11 shrink-0 items-center justify-center print:hidden"
          >
            <Icon name="close" />
          </button>
        </div>

        {documents.length > 0 && (
          <section className="mt-6">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-lg">Gather these first</h3>
              <p className="text-sm text-muted tabular-nums" aria-live="polite">
                {done} of {documents.length} ready
              </p>
            </div>
            <ul className="mt-2 divide-y divide-divider overflow-hidden rounded-lg border border-border">
              {documents.map((doc) => (
                <li key={doc}>
                  <label className="flex min-h-12 items-start gap-3 px-3 py-3 hover:bg-primary-lighter">
                    <input
                      type="checkbox"
                      checked={!!checked[doc]}
                      onChange={() => setChecked((c) => ({ ...c, [doc]: !c[doc] }))}
                      className="mt-0.5 h-5 w-5 shrink-0"
                    />
                    <span className={checked[doc] ? "line-through" : ""}>{doc}</span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        )}

        {actions.length > 0 && (
          <section className="mt-7">
            <h3 className="text-lg">Then follow these steps</h3>
            <ol className="mt-3 space-y-4">
              {actions.map((s, i) => (
                <li key={`${s.step}-${s.action}`} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center bg-primary-dark text-sm font-bold text-white tabular-nums">
                    {i + 1}
                  </span>
                  <div className="pt-0.5">
                    <p className="font-semibold">
                      {s.action}
                      {s.time_required && <span className="font-normal text-muted"> ({s.time_required})</span>}
                    </p>
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noreferrer" className="break-all">
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
          <p className="mt-7 flex items-center gap-2">
            <Icon name="clock" className="h-5 w-5" />
            <span><span className="font-semibold">Processing time:</span> {program.processing_time}</span>
          </p>
        )}
        {program.tip && <p className="mt-4 border-l-8 border-info bg-info-bg p-4">{program.tip}</p>}
        {program.source && <p className="mt-4 text-sm text-muted">Source: {program.source}</p>}

        <div className="mt-7 flex flex-wrap gap-3 print:hidden">
          {program.application_url && (
            <a href={program.application_url} target="_blank" rel="noreferrer" className="btn btn-primary">
              Apply now
              <Icon name="external" className="h-4 w-4" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          )}
          <button type="button" onClick={() => window.print()} className="btn btn-secondary">
            <Icon name="printer" className="h-4 w-4" />
            Print this plan
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
