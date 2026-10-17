// Application tracker. Needs sign in (see App.jsx). Everything is saved in this browser per user.
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import TrackerEntry from "../components/tracker/TrackerEntry.jsx";
import { LinkButton } from "../components/ui/index.jsx";
import { summarizeAnswers } from "../lib/quizSchema.js";
import { usePageTitle } from "../lib/usePageTitle.js";
import { STATUSES, getAnswers, getResults, getTracker, removeTrackerEntry, scopeFor, updateTrackerEntry } from "../lib/userData.js";

export default function Tracker() {
  usePageTitle("Your applications");
  const { user } = useAuth();
  const [entries, setEntries] = useState(() => getTracker(user.email));
  const [announce, setAnnounce] = useState("");
  const headingRef = useRef(null);
  const scope = scopeFor(user.email);
  const answers = getAnswers(scope)?.answers;
  const hasResults = !!getResults(scope);
  const rows = summarizeAnswers(answers);

  const counts = STATUSES.map((s) => [s, entries.filter((e) => e.status === s).length]).filter(([, n]) => n > 0);

  const onChange = (id, patch) => setEntries(updateTrackerEntry(user.email, id, patch));
  const onRemove = (entry) => {
    setEntries(removeTrackerEntry(user.email, entry.id));
    setAnnounce(`${entry.name} was removed.`);
    headingRef.current?.focus();
  };

  return (
    <div className="container-page py-8 lg:py-12">
      <h1 ref={headingRef} tabIndex={-1} className="outline-none">Your applications</h1>
      <p role="status" className="mt-2 font-semibold">{announce}</p>
      <p className="mt-2 max-w-[65ch] text-lg">
        {entries.length
          ? `${entries.length} ${entries.length === 1 ? "program" : "programs"} tracked: ${counts.map(([s, n]) => `${n} ${s.toLowerCase()}`).join(", ")}.`
          : "Keep the status, dates and documents for each program you apply to in one place."}
      </p>

      <section aria-labelledby="answers-title" className="mt-8 rounded-lg border border-border border-l-8 border-l-accent bg-surface-alt p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="answers-title" className="text-xl">Your answers</h2>
          <Link to="/quiz" className="font-semibold">Edit your answers</Link>
        </div>
        {rows.length ? (
          <dl className="mt-3 grid gap-x-8 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
            {rows.map((r) => (
              <div key={r.label} className="flex gap-2"><dt className="font-semibold">{r.label}:</dt><dd>{r.value}</dd></div>
            ))}
          </dl>
        ) : (
          <p className="mt-2">You haven't answered the questions yet. <Link to="/quiz">Take the quiz</Link></p>
        )}
      </section>

      <section aria-labelledby="apps-title" className="mt-10">
        <h2 id="apps-title" className="sr-only">Tracked programs</h2>
        {entries.length ? (
          <ul className="space-y-6">
            {entries.map((e) => <TrackerEntry key={e.id} entry={e} onChange={onChange} onRemove={onRemove} />)}
          </ul>
        ) : (
          <div className="rounded-lg border-2 border-border p-6">
            <h3>You haven't added any programs yet</h3>
            <p className="mt-2">Select I applied on a match to start tracking it here.</p>
            <div className="mt-4">
              <LinkButton to={hasResults ? "/matches" : "/quiz"}>{hasResults ? "See your matches" : "Take the quiz"}</LinkButton>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
