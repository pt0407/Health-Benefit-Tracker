// One matched program. Estimate wording is the labelling Person 3 chose (PR #18).
import { useState } from "react";
import { Link } from "react-router-dom";
import { CATEGORY_ICONS, CATEGORY_LABELS, LEVEL_LABELS } from "../../lib/programMeta.js";
import ActionPlan from "../Results/ActionPlan.jsx";
import Icon from "../shared/Icon.jsx";
import { Button, Tag } from "../ui/index.jsx";

const STRENGTH = {
  high: { label: "Strong match", steps: 3, tone: "success" },
  medium: { label: "Possible match", steps: 2, tone: "primary" },
  low: { label: "Worth checking", steps: 1, tone: "neutral" },
};

const usd = (v) => `$${Math.round(v).toLocaleString()}`;

// Strength is shown as text and as filled squares (shape), never by color alone.
function Strength({ confidence }) {
  const s = STRENGTH[confidence] ?? STRENGTH.low;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="flex gap-0.5" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <span key={i} className={`h-3 w-3 rounded-[2px] border-2 border-primary-dark ${i <= s.steps ? "bg-primary-dark" : "bg-white"}`} />
        ))}
      </span>
      <Tag tone={s.tone} className="rounded-full px-3">{s.label}</Tag>
    </span>
  );
}

export default function MatchCard({ program, inTracker, onApply }) {
  const [open, setOpen] = useState(false);
  const headingId = `match-${program.program_id || program.program.replace(/\W+/g, "-")}`;
  const days = program.processingDays != null ? `Up to ${program.processingDays} days` : program.processing_time || "Not stated";

  return (
    <li className="overflow-hidden rounded-lg border-2 border-primary-light bg-white transition-colors hover:border-primary">
      <article aria-labelledby={headingId}>
        <div className="flex gap-4 p-5">
          <span
            aria-hidden="true"
            className="arch-badge flex h-16 w-12 shrink-0 items-end justify-center bg-primary-dark pb-3 text-white"
          >
            <Icon name={CATEGORY_ICONS[program.category] ?? "list"} className="h-5 w-5" />
          </span>
          <div className="grid min-w-0 flex-1 gap-3 md:grid-cols-[1fr_auto]">
            <div>
              <h3 id={headingId}>{program.program}</h3>
              <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted">
                <div><dt className="sr-only">Type</dt><dd className="font-semibold text-primary-dark">{CATEGORY_LABELS[program.category] ?? "Other"}</dd></div>
                <div><dt className="sr-only">Level</dt><dd>{LEVEL_LABELS[program.level] ?? "Not listed"}</dd></div>
                <div className="flex items-center gap-1.5">
                  <Icon name="clock" className="h-4 w-4" />
                  <dt className="sr-only">Processing time</dt><dd>{days}</dd>
                </div>
              </dl>
              <p className="mt-3 max-w-[70ch]">{program.reason}</p>
            </div>
            <div className="md:text-right">
              <Strength confidence={program.confidence} />
              {program.monthly_value_usd > 0 ? (
                <p className="mt-3 text-3xl font-extrabold tracking-tight text-primary-dark tabular-nums">
                  Est. {usd(program.monthly_value_usd)}<span className="text-lg font-bold">/mo</span>
                </p>
              ) : (
                <p className="mt-3 text-lg font-bold text-primary-dark">Health coverage</p>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t-2 border-primary-light bg-primary-lighter px-5 py-3">
          <Button variant="secondary" onClick={() => setOpen(true)}>
            <Icon name="list" className="h-4 w-4" />
            How to apply
          </Button>
          {program.application_url && (
            <a href={program.application_url} target="_blank" rel="noreferrer" className="btn btn-secondary">
              Apply on the official site
              <Icon name="external" className="h-4 w-4" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          )}
          {inTracker ? (
            <p className="flex items-center gap-3 font-semibold">
              <Icon name="check" className="h-5 w-5" />
              In your tracker
              <Link to="/tracker">View tracker</Link>
            </p>
          ) : (
            <Button onClick={() => onApply(program)}>I applied</Button>
          )}
        </div>
        {program.source && <p className="px-5 py-3 text-sm text-muted">Source: {program.source}</p>}
      </article>
      {open && <ActionPlan program={program} onClose={() => setOpen(false)} />}
    </li>
  );
}
