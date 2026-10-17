// One tracked application. Every field is editable and saves to this browser as you type.
import { useEffect, useRef, useState } from "react";
import { CATEGORY_LABELS, LEVEL_LABELS } from "../../lib/programMeta.js";
import { STATUSES } from "../../lib/userData.js";
import Icon from "../shared/Icon.jsx";
import { Button, Tag } from "../ui/index.jsx";

const TONES = {
  "Not started": "neutral", Preparing: "warning", Submitted: "primary",
  "Under review": "primary", Approved: "success", Denied: "error",
};

export default function TrackerEntry({ entry, onChange, onRemove }) {
  const [confirming, setConfirming] = useState(false);
  const [number, setNumber] = useState(entry.confirmationNumber);
  const [notes, setNotes] = useState(entry.notes);
  const [saved, setSaved] = useState(false);
  const timer = useRef(null);
  const id = `entry-${entry.id}`;
  const ready = entry.documents.filter((d) => d.done).length;

  useEffect(() => () => clearTimeout(timer.current), []);

  const save = (patch) => {
    onChange(entry.id, patch);
    setSaved(true);
  };
  // Text is saved shortly after typing stops, and immediately when the field loses focus.
  const typed = (patch) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => save(patch), 400);
  };

  return (
    <li className="overflow-hidden rounded-lg border-2 border-primary-light bg-white" id={id}>
      <article aria-labelledby={`${id}-title`}>
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-divider p-5">
          <div>
            <h2 id={`${id}-title`} className="text-xl">{entry.name}</h2>
            <p className="mt-1 text-muted">
              {CATEGORY_LABELS[entry.category] ?? "Other"}, {LEVEL_LABELS[entry.level] ?? "Not listed"}
              {entry.monthlyValue > 0 ? `, est. $${Math.round(entry.monthlyValue).toLocaleString()}/mo` : ", health coverage"}
            </p>
            {entry.applicationUrl && (
              <p className="mt-1">
                <a href={entry.applicationUrl} target="_blank" rel="noreferrer">
                  Official site<span className="sr-only"> for {entry.name} (opens in a new tab)</span>
                </a>
              </p>
            )}
          </div>
          <Tag tone={TONES[entry.status] ?? "neutral"}>Status: {entry.status}</Tag>
        </div>

        <div className="grid gap-5 p-5 md:grid-cols-2">
          <div>
            <label htmlFor={`${id}-status`} className="block font-semibold">Status</label>
            <select id={`${id}-status`} className="input mt-1" value={entry.status} onChange={(e) => save({ status: e.target.value })}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor={`${id}-date`} className="block font-semibold">Date applied</label>
            <input id={`${id}-date`} type="date" className="input mt-1" value={entry.dateApplied || ""} onChange={(e) => save({ dateApplied: e.target.value })} />
          </div>
          <div>
            <label htmlFor={`${id}-number`} className="block font-semibold">Confirmation number</label>
            <p id={`${id}-number-hint`} className="text-muted">From your confirmation email or letter</p>
            <input
              id={`${id}-number`} type="text" className="input mt-1" value={number} aria-describedby={`${id}-number-hint`}
              onChange={(e) => { setNumber(e.target.value); typed({ confirmationNumber: e.target.value }); }}
              onBlur={() => { clearTimeout(timer.current); if (number !== entry.confirmationNumber) save({ confirmationNumber: number }); }}
            />
          </div>
          <fieldset className="md:row-span-2">
            <legend className="font-semibold">Documents checklist</legend>
            {entry.documents.length ? (
              <>
                <p className="text-muted tabular-nums" aria-live="polite">{ready} of {entry.documents.length} ready</p>
                <div className="mt-1 divide-y divide-divider overflow-hidden rounded-lg border border-border">
                  {entry.documents.map((d, i) => (
                    <label key={d.label} className="flex min-h-11 items-start gap-3 px-3 py-2 hover:bg-primary-lighter">
                      <input
                        type="checkbox" className="mt-0.5 h-5 w-5 shrink-0" checked={d.done}
                        onChange={() => save({ documents: entry.documents.map((x, j) => (j === i ? { ...x, done: !x.done } : x)) })}
                      />
                      <span>{d.label}</span>
                    </label>
                  ))}
                </div>
              </>
            ) : (
              <p className="mt-1 text-muted">No document list is available for this program.</p>
            )}
          </fieldset>
          <div>
            <label htmlFor={`${id}-notes`} className="block font-semibold">Notes</label>
            <textarea
              id={`${id}-notes`} rows={4} className="input mt-1" value={notes}
              onChange={(e) => { setNotes(e.target.value); typed({ notes: e.target.value }); }}
              onBlur={() => { clearTimeout(timer.current); if (notes !== entry.notes) save({ notes }); }}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-divider bg-surface-alt px-5 py-3">
          <p role="status" className="text-sm text-muted">{saved ? "Saved in this browser." : "Changes save automatically."}</p>
          {confirming ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-semibold">Remove {entry.name} from your tracker? This can't be undone.</p>
              <Button variant="danger" onClick={() => onRemove(entry)}>Yes, remove</Button>
              <Button variant="secondary" onClick={() => setConfirming(false)}>Cancel</Button>
            </div>
          ) : (
            <Button variant="danger" onClick={() => setConfirming(true)}>
              <Icon name="trash" className="h-4 w-4" />
              Remove from tracker
            </Button>
          )}
        </div>
      </article>
    </li>
  );
}
