// Results page. Dollar values are estimates, labeled as Person 3 chose (see PR #18).
// Filters and sort live in the URL, so a reload or the sign in round trip keeps them.
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import MatchCard from "../components/matches/MatchCard.jsx";
import Icon from "../components/shared/Icon.jsx";
import LoadingScreen from "../components/ui/LoadingScreen.jsx";
import { Alert, Button, LinkButton } from "../components/ui/index.jsx";
import { BUCKETS, CATEGORY_LABELS, enrich, levelMatches } from "../lib/programMeta.js";
import { summarizeAnswers, toProfile } from "../lib/quizSchema.js";
import { exportWorksheetPdf } from "../api/benefitsApi.js";
import { useProgramCatalog } from "../lib/useProgramCatalog.js";
import { usePageTitle } from "../lib/usePageTitle.js";
import { addTrackerEntry, getAnswers, getResults, getTracker, scopeFor, setPendingApply } from "../lib/userData.js";

const usd = (v) => `$${Math.round(v).toLocaleString()}`;
const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;
const RANK = { high: 0, medium: 1, low: 2 };

const SORTS = [
  { value: "value-desc", label: "Estimated value, highest first" },
  { value: "value-asc", label: "Estimated value, lowest first" },
  { value: "strength", label: "Match strength" },
  { value: "name", label: "Program name, A to Z" },
];

// Health coverage has no dollar value, so it always sorts after valued programs.
function sortPrograms(list, sort) {
  const v = (p) => p.monthly_value_usd || 0;
  const copy = [...list];
  if (sort === "name") return copy.sort((a, b) => a.program.localeCompare(b.program));
  if (sort === "strength") return copy.sort((a, b) => RANK[a.confidence] - RANK[b.confidence] || v(b) - v(a));
  if (sort === "value-asc") return copy.sort((a, b) => (v(a) > 0 ? 0 : 1) - (v(b) > 0 ? 0 : 1) || v(a) - v(b));
  return copy.sort((a, b) => v(b) - v(a));
}

const toggle = (list, value) => (list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);

export default function Matches() {
  usePageTitle("Your matches");
  const { user } = useAuth();
  const scope = scopeFor(user?.email);
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const catalog = useProgramCatalog();
  const [flash, setFlash] = useState(location.state?.flash ?? null);
  const [added, setAdded] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [tracked, setTracked] = useState(() => (user ? getTracker(user.email).map((e) => e.id) : []));

  useEffect(() => {
    setTracked(user ? getTracker(user.email).map((e) => e.id) : []);
  }, [user, flash]);

  const saved = useMemo(() => getResults(scope), [scope]);
  const answers = useMemo(() => getAnswers(scope)?.answers, [scope]);
  const result = saved?.result;

  const programs = useMemo(
    () => (result ? result.matched_programs.map((m) => enrich(m, catalog.byId)) : []),
    [result, catalog.byId],
  );

  const sort = params.get("sort") || "value-desc";
  const cats = (params.get("cat") || "").split(",").filter(Boolean);
  const level = params.get("level") || "all";
  const times = (params.get("time") || "").split(",").filter(Boolean);
  const setParam = (key, value) =>
    setParams((p) => {
      const n = new URLSearchParams(p);
      if (!value || value === "all" || (key === "sort" && value === "value-desc")) n.delete(key);
      else n.set(key, value);
      return n;
    }, { replace: true });
  const activeFilters = cats.length + times.length + (level !== "all" ? 1 : 0);

  const visible = useMemo(
    () =>
      sortPrograms(
        programs.filter(
          (p) =>
            (!cats.length || cats.includes(p.category)) &&
            levelMatches(p.level, level) &&
            (!times.length || times.includes(p.bucket)),
        ),
        sort,
      ),
    [programs, params], // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (!result) {
    return (
      <div className="container-page max-w-2xl py-16">
        <h1>No results yet</h1>
        <p className="mt-3 text-lg">Answer the 10 questions first, and Civis will show the programs your household may qualify for.</p>
        <LinkButton to="/quiz" className="mt-8">Take the quiz</LinkButton>
      </div>
    );
  }

  function onApply(program) {
    if (!user) {
      setPendingApply(program);
      navigate(`/signin?next=${encodeURIComponent(location.pathname + location.search)}`);
      return;
    }
    const r = addTrackerEntry(user.email, program);
    setTracked(r.entries.map((e) => e.id));
    setAdded(`${program.program} was added to your tracker.`);
  }

  // The match list is joined with the program catalog, so keep the same loader up until it arrives.
  if (catalog.status === "loading") return <LoadingScreen />;

  const count = result.program_count;
  const strong = result.matched_programs.filter((p) => p.confidence === "high").length;
  const hasValues = result.matched_programs.some((p) => p.monthly_value_usd > 0);
  const catCounts = programs.reduce((acc, p) => ({ ...acc, [p.category]: (acc[p.category] || 0) + 1 }), {});
  const bucketCounts = programs.reduce((acc, p) => ({ ...acc, [p.bucket]: (acc[p.bucket] || 0) + 1 }), {});
  const message = flash || added;

  async function downloadPdf() {
    if (!result || !answers) return;
    setExporting(true);
    setExportError(null);
    try {
      await exportWorksheetPdf(toProfile(answers), result);
    } catch {
      setExportError("We couldn't create your worksheet. Check your connection and try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="container-page py-8 lg:py-12">
      {message && (
        <Alert variant="success" title="Added to your tracker" className="mb-6" onDismiss={() => { setFlash(null); setAdded(null); }}>
          <p>{message} <Link to="/tracker">View your tracker</Link></p>
        </Alert>
      )}

      <section aria-labelledby="summary-title" className="border-b border-divider pb-8">
        <h1 id="summary-title">
          {count > 0 ? `${plural(count, "program")} may fit your household` : "We didn't find a clear match"}
        </h1>
        {count > 0 ? (
          <>
            <p className="mt-4 max-w-[65ch] text-xl">
              {result.total_estimated_annual_value > 0 ? (
                <>
                  You may qualify for up to an estimated{" "}
                  <strong className="tabular-nums">{usd(result.total_estimated_annual_value)}/year</strong>{" "}
                  (about <span className="tabular-nums">{usd(result.total_estimated_monthly_value)}</span>/mo). Health coverage isn't counted in that total.
                </>
              ) : (
                "Health coverage and other non-cash programs don't have a dollar total."
              )}
            </p>
            {strong > 0 && <p className="mt-3 font-semibold">{plural(strong, "strong match", "strong matches")}</p>}
            <details className="mt-5 max-w-[70ch]">
              <summary className="font-semibold text-primary underline">What these estimates mean</summary>
              <div className="mt-3 space-y-3 border-l-4 border-border pl-4">
                {hasValues && (
                  <p>
                    Dollar amounts are estimates based on program averages and your answers. They are not a guarantee of
                    benefits. Actual amounts depend on your full application and caseworker review.
                  </p>
                )}
                <p>
                  Health coverage is shown without a dollar amount because the figure is what the government spends per
                  person, not money you receive.
                </p>
                <p>
                  Programs marked &quot;Value varies&quot; help in ways that have no single dollar figure, such as tax credits paid
                  once a year, legal aid and early learning.
                </p>
              </div>
            </details>
          </>
        ) : (
          <p className="mt-4 max-w-[65ch] text-lg">
            Program rules change and have exceptions, so it's still worth checking{" "}
            <a href="https://www.usa.gov/benefits" target="_blank" rel="noreferrer">USA.gov's benefit finder<span className="sr-only"> (opens in a new tab)</span></a>{" "}
            directly.
          </p>
        )}

        <div className="mt-6 rounded-lg border border-border border-l-8 border-l-accent bg-surface-alt p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg">Based on your answers</h2>
            <Link to="/quiz" className="font-semibold">Edit your answers</Link>
          </div>
          {answers ? (
            <dl className="mt-2 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
              {summarizeAnswers(answers).map((r) => (
                <div key={r.label} className="flex gap-2"><dt className="font-semibold">{r.label}:</dt><dd>{r.value}</dd></div>
              ))}
            </dl>
          ) : (
            <p className="mt-2 text-sm">Your answers are no longer saved in this browser. Take the quiz again to update them.</p>
          )}
        </div>

        {result.warnings?.length > 0 && (
          <Alert variant="warning" title="Worth knowing" className="mt-6">
            <ul className="space-y-1">{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          </Alert>
        )}
      </section>

      {count > 0 && (
        <div className="mt-8 grid gap-8 lg:grid-cols-[17rem_1fr]">
          <div>
            <Button variant="secondary" className="w-full lg:hidden" aria-expanded={filtersOpen} aria-controls="filters" onClick={() => setFiltersOpen((o) => !o)}>
              <Icon name="filter" className="h-4 w-4" />
              Filter results{activeFilters ? ` (${activeFilters})` : ""}
            </Button>
            <form id="filters" aria-label="Filter results" onSubmit={(e) => e.preventDefault()} className={`${filtersOpen ? "block" : "hidden"} mt-4 space-y-6 rounded-lg border border-border p-4 lg:mt-0 lg:block`}>
              <h2 className="hidden text-xl lg:block">Filter results</h2>
              <fieldset>
                <legend className="font-bold">Type of help</legend>
                <div className="mt-1 space-y-0.5">
                  {Object.keys(catCounts).sort().map((c) => (
                    <label key={c} className="flex min-h-11 items-center gap-3">
                      <input type="checkbox" className="h-5 w-5" checked={cats.includes(c)} onChange={() => setParam("cat", toggle(cats, c).join(","))} />
                      <span>{CATEGORY_LABELS[c] ?? "Other"} <span className="text-muted">({catCounts[c]})</span></span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <fieldset>
                <legend className="font-bold">Federal or Texas</legend>
                <div className="mt-1 space-y-0.5">
                  {[["all", "All programs"], ["federal", "Federal"], ["texas", "Texas"]].map(([v, l]) => (
                    <label key={v} className="flex min-h-11 items-center gap-3">
                      <input type="radio" name="level" className="h-5 w-5" checked={level === v} onChange={() => setParam("level", v)} />
                      {l}
                    </label>
                  ))}
                </div>
              </fieldset>
              <fieldset>
                <legend className="font-bold">Processing time</legend>
                <div className="mt-1 space-y-0.5">
                  {BUCKETS.filter((b) => bucketCounts[b.value]).map((b) => (
                    <label key={b.value} className="flex min-h-11 items-center gap-3">
                      <input type="checkbox" className="h-5 w-5" checked={times.includes(b.value)} onChange={() => setParam("time", toggle(times, b.value).join(","))} />
                      <span>{b.label} <span className="text-muted">({bucketCounts[b.value]})</span></span>
                    </label>
                  ))}
                </div>
              </fieldset>
              <Button variant="secondary" disabled={!activeFilters} onClick={() => setParams((p) => { const n = new URLSearchParams(); if (p.get("sort")) n.set("sort", p.get("sort")); return n; }, { replace: true })}>
                Clear filters
              </Button>
            </form>
          </div>

          <section aria-label="Matched programs">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p role="status" className="font-semibold">Showing {visible.length} of {programs.length} programs</p>
                {answers && (
                  <Button variant="secondary" className="mt-3" onClick={downloadPdf} disabled={exporting}>
                    {exporting ? "Preparing your worksheet…" : "Download worksheet (PDF)"}
                  </Button>
                )}
                {exportError && <p role="alert" className="mt-2 text-sm text-red-700">{exportError}</p>}
              </div>
              <div>
                <label htmlFor="sort" className="block font-semibold">Sort by</label>
                <select id="sort" className="input mt-1 min-w-64" value={sort} onChange={(e) => setParam("sort", e.target.value)}>
                  {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
            </div>
            {visible.length ? (
              <ul className="mt-5 space-y-5">
                {visible.map((p) => (
                  <MatchCard key={p.program_id || p.program} program={p} inTracker={tracked.includes(p.program_id || p.program.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))} onApply={onApply} />
                ))}
              </ul>
            ) : (
              <div className="mt-5 rounded-lg border-2 border-border p-6">
                <h2 className="text-xl">No programs match these filters</h2>
                <Button variant="secondary" className="mt-4" onClick={() => setParams({}, { replace: true })}>Clear filters</Button>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
