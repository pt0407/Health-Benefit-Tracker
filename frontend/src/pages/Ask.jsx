// Ask Civis: questions about benefits, answered from the program records only
// (POST /api/ask). Owner: Person 4. Answers render as plain text, never HTML.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { askCivis } from "../api/benefitsApi.js";
import { useAuth } from "../auth/AuthContext.jsx";
import Icon from "../components/shared/Icon.jsx";
import { Alert, Button } from "../components/ui/index.jsx";
import { toProfile } from "../lib/quizSchema.js";
import { usePageTitle } from "../lib/usePageTitle.js";
import { getAnswers, getResults, scopeFor } from "../lib/userData.js";

const MAX_CHARS = 500;
const HISTORY_TURNS = 6;

const SUGGESTIONS = [
  "Can I get WIC if I'm not a citizen?",
  "What counts as income for SNAP?",
  "I'm pregnant. What health coverage can I get in Texas?",
  "Is there help paying my electric bill?",
  "How do I get a free or cheap phone?",
];

function errorMessage(err) {
  const status = err?.response?.status;
  if (status === 429) return "You've asked a lot of questions in a short time. Please wait a few minutes and try again.";
  if (status === 503) return "Civis is still setting up its program records. Please try again in a few minutes.";
  return "Civis couldn't answer right now. Check your connection and try again.";
}

function Answer({ turn }) {
  return (
    <div className="max-w-[65ch]">
      <p className="whitespace-pre-line">{turn.content}</p>
      {!turn.answeredFromRecords && (
        <p className="mt-2 text-sm text-muted">
          Civis's program records don't fully cover this. For a sure answer, ask the agency or call 2-1-1 Texas.
        </p>
      )}
      {turn.sources?.length > 0 && (
        <div className="mt-3 border-t border-divider pt-2">
          <p className="text-sm font-semibold">Sources</p>
          <ul className="mt-1 space-y-1 text-sm">
            {turn.sources.map((s) => (
              <li key={s.program_id}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.program_name}
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Ask() {
  usePageTitle("Ask Civis");
  const { user } = useAuth();
  const scope = scopeFor(user?.email);
  const answers = getAnswers(scope)?.answers;
  const hasProfile = !!(answers && getResults(scope));
  const [usePersonal, setUsePersonal] = useState(hasProfile);
  const [turns, setTurns] = useState([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [turns, pending]);

  async function send(text) {
    const question = text.trim();
    if (question.length < 2 || pending) return;
    setError(null);
    setPending(true);
    const history = turns.slice(-HISTORY_TURNS).map((t) => ({ role: t.role, content: t.content }));
    setTurns((t) => [...t, { role: "user", content: question }]);
    setDraft("");
    try {
      let profile;
      if (usePersonal && hasProfile) {
        try { profile = toProfile(answers); } catch { profile = undefined; }
      }
      const res = await askCivis({ question, history, profile });
      setTurns((t) => [...t, {
        role: "assistant", content: res.answer, sources: res.sources, answeredFromRecords: res.answered_from_records,
      }]);
    } catch (err) {
      // Put the question back so nothing typed is lost.
      setTurns((t) => t.slice(0, -1));
      setDraft(question);
      setError(errorMessage(err));
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="container-page max-w-3xl py-8 lg:py-12">
      <h1>Ask Civis</h1>
      <p className="mt-4 max-w-[65ch] text-lg">
        Ask anything about benefit programs: who qualifies, what counts as income, what to bring, how to apply.
        Civis answers only from official program records and shows where each answer comes from.
      </p>

      {hasProfile ? (
        <label className="mt-5 flex max-w-[65ch] items-start gap-3">
          <input type="checkbox" className="mt-1 h-5 w-5 shrink-0" checked={usePersonal} onChange={(e) => setUsePersonal(e.target.checked)} />
          <span>
            Use my quiz answers so Civis can answer for my household.{" "}
            <span className="text-muted">They're sent with each question and not saved.</span>
          </span>
        </label>
      ) : (
        <p className="mt-5 text-muted">
          <Link to="/quiz">Take the quiz</Link> first if you want answers about your own household.
        </p>
      )}

      <section aria-label="Conversation" className="mt-8">
        <ol role="log" aria-live="polite" aria-relevant="additions" className="space-y-5">
          {turns.map((t, i) => (
            <li key={i} className={t.role === "user" ? "flex justify-end" : "flex"}>
              {t.role === "user" ? (
                <div className="max-w-[85%] rounded-lg bg-primary px-4 py-3 text-white">
                  <span className="sr-only">You asked: </span>
                  <p className="whitespace-pre-line">{t.content}</p>
                </div>
              ) : (
                <div className="w-full rounded-lg border border-border bg-white px-4 py-3">
                  <p className="mb-1 flex items-center gap-2 text-sm font-bold text-primary-dark">
                    <Icon name="check" className="h-4 w-4" />
                    Civis
                  </p>
                  <Answer turn={t} />
                </div>
              )}
            </li>
          ))}
          {pending && (
            <li className="flex items-center gap-3 text-muted" role="status">
              <span className="civis-spinner h-5 w-5 rounded-full border-2 border-divider border-t-primary" aria-hidden="true" />
              Civis is reading the program records…
            </li>
          )}
        </ol>
        <div ref={endRef} />

        {turns.length === 0 && !pending && (
          <div className="rounded-lg bg-surface-alt p-4">
            <h2 className="text-lg">Try asking</h2>
            <ul className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <Button variant="secondary" className="min-h-11 text-left font-semibold" onClick={() => send(s)}>{s}</Button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {error && <Alert variant="error" title="No answer this time" className="mt-6"><p>{error}</p></Alert>}

      <form
        className="mt-6"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <label htmlFor="ask-input" className="block font-semibold">Your question</label>
        <textarea
          id="ask-input"
          ref={inputRef}
          rows={3}
          maxLength={MAX_CHARS}
          value={draft}
          aria-describedby="ask-hint"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send(draft);
            }
          }}
          className="input mt-1 resize-y"
          placeholder="For example: Do I need a Social Security number to apply for SNAP?"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <p id="ask-hint" className="text-sm text-muted tabular-nums">
            Press Enter to send, Shift+Enter for a new line. {draft.length}/{MAX_CHARS}
          </p>
          <div className="flex gap-3">
            {turns.length > 0 && (
              <Button variant="secondary" disabled={pending} onClick={() => { setTurns([]); setError(null); }}>
                Start over
              </Button>
            )}
            <Button type="submit" disabled={pending || draft.trim().length < 2}>
              {pending ? "Asking…" : "Ask"}
            </Button>
          </div>
        </div>
      </form>

      <p className="mt-8 max-w-[65ch] text-sm text-muted">
        Civis can make mistakes. It is not a government website, and only the agency that runs a program can decide if
        you qualify. Don't type private details like your Social Security number.
      </p>
    </div>
  );
}
