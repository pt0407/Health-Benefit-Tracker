// Owner: Person 3 (restyled for Civis). See docs/BUILD_PLAN.md section 3, Component 2.
// The question order, validation and the UserProfile payload are unchanged. Answers
// are saved in this browser as you go, so "Edit your answers" reopens them pre-filled.

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import { matchBenefits } from "../../api/benefitsApi.js";
import {
  CITIZENSHIP, EMPLOYMENT, INCOME_BRACKETS, INITIAL, INSURANCE, US_STATES,
  normalizeAnswers, toProfile,
} from "../../lib/quizSchema.js";
import { clearAnswers, getAnswers, saveAnswers, saveResults, scopeFor } from "../../lib/userData.js";
import { usePageTitle } from "../../lib/usePageTitle.js";
import Icon from "../shared/Icon.jsx";
import LoadingScreen from "../ui/LoadingScreen.jsx";
import { Alert, Button } from "../ui/index.jsx";

const YES_NO = [{ value: true, label: "Yes" }, { value: false, label: "No" }];
const yesNo = (v) => (v == null ? null : v ? "Yes" : "No");
const isInt = (v, lo, hi) => Number.isInteger(v) && v >= lo && v <= hi;

// One validity rule per question, in order. Used for Next, for jumping back, and to
// find where a saved draft left off.
const RULES = [
  (f) => !!f.state,
  (f) => isInt(f.household_size, 1, 20),
  (f) => f.income_bracket != null,
  (f) => !!f.employment_status,
  (f) => isInt(f.age, 0, 120),
  (f) => f.has_children === false || (f.has_children === true && f.children_ages.length >= 1 && f.children_ages.every((a) => isInt(a, 0, 18))),
  (f) => f.is_pregnant != null,
  (f) => f.has_disability === false || (f.has_disability === true && f.receiving_disability_benefits != null),
  (f) => !!f.insurance_status,
  (f) => !!f.citizenship,
];

function firstInvalid(form) {
  const i = RULES.findIndex((r) => !r(form));
  return i === -1 ? RULES.length - 1 : i;
}

// Native radio buttons styled as large tiles: arrow keys work, the checked state shows a dot, not just color.
function ChoiceTiles({ name, options, value, onChange, labelledBy = "question-title", describedBy }) {
  return (
    <fieldset aria-labelledby={labelledBy} aria-describedby={describedBy} className="mt-6 flex flex-col gap-2">
      {options.map((o) => (
        <label
          key={String(o.value)}
          className="flex min-h-14 items-center gap-3 rounded-lg border-2 border-ink bg-white px-4 py-2 text-lg has-[:checked]:border-primary has-[:checked]:bg-primary-light has-[:checked]:font-semibold"
        >
          <input
            type="radio"
            name={name}
            checked={value === o.value}
            onChange={() => onChange(o.value)}
            className="h-6 w-6 shrink-0"
          />
          {o.label}
        </label>
      ))}
    </fieldset>
  );
}

function NumberInput({ id, value, onChange, min, max, placeholder, labelledBy = "question-title", describedBy, className = "mt-6 max-w-48", invalid }) {
  return (
    <input
      id={id}
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      value={value ?? ""}
      placeholder={placeholder}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      aria-invalid={invalid ? "true" : undefined}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className={`input tabular-nums ${className}`}
    />
  );
}

export default function QuizWizard() {
  usePageTitle("Check benefits");
  const { user } = useAuth();
  const scope = scopeFor(user?.email);
  const navigate = useNavigate();

  // Saved answers are read once when the quiz opens.
  const [initial] = useState(() => getAnswers(scope));
  const [form, setForm] = useState(() => normalizeAnswers(initial?.answers));
  const [step, setStep] = useState(() => (initial && !initial.complete ? firstInvalid(normalizeAnswers(initial.answers)) : 0));
  const [furthest, setFurthest] = useState(() =>
    initial ? (initial.complete ? RULES.length - 1 : firstInvalid(normalizeAnswers(initial.answers))) : 0,
  );
  const [restored, setRestored] = useState(!!initial);
  const [showError, setShowError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const titleRef = useRef(null);
  const firstRender = useRef(true);
  const dirty = useRef(false);

  // Save a draft after every change (never overwrite saved answers with the empty form).
  useEffect(() => {
    if (dirty.current) saveAnswers(scope, form, { complete: false });
  }, [form, scope]);

  // Move focus to each new question so screen readers announce it.
  useEffect(() => {
    setShowError(false);
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    titleRef.current?.focus();
    setFurthest((f) => Math.max(f, step));
  }, [step]);

  const set = (key, value) => {
    dirty.current = true;
    setForm((f) => ({ ...f, [key]: value }));
  };
  const update = (fn) => {
    dirty.current = true;
    setForm(fn);
  };

  const errId = showError ? "question-error" : undefined;
  const steps = [
    {
      key: "state", label: "State", summary: () => form.state,
      title: "What state do you live in?",
      hint: "We check federal programs everywhere and Texas state programs in Texas.",
      problem: "Choose a state.",
      body: (
        <select id="state" value={form.state} aria-labelledby="question-title" onChange={(e) => set("state", e.target.value)} className="input mt-6 max-w-48">
          {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      ),
    },
    {
      key: "household_size", label: "Household",
      summary: () => form.household_size && `${form.household_size} ${form.household_size === 1 ? "person" : "people"}`,
      title: "How many people live in your household?",
      hint: "Include yourself, your spouse, and anyone you support.",
      problem: "Enter a whole number from 1 to 20.",
      body: <NumberInput id="household" value={form.household_size} min={1} max={20} placeholder="For example, 4" describedBy={errId} invalid={showError} onChange={(v) => set("household_size", v)} />,
    },
    {
      key: "income", label: "Income", summary: () => INCOME_BRACKETS.find((b) => b.value === form.income_bracket)?.label,
      title: "What is your approximate annual household income?",
      hint: "Before taxes, for everyone in the household combined.",
      problem: "Choose an income range.",
      body: (
        <ChoiceTiles
          name="income" options={INCOME_BRACKETS} value={form.income_bracket} describedBy={errId}
          onChange={(v) => {
            const b = INCOME_BRACKETS.find((x) => x.value === v);
            update((f) => ({ ...f, income_bracket: b.value, annual_income: b.income }));
          }}
        />
      ),
    },
    {
      key: "employment_status", label: "Work", summary: () => EMPLOYMENT.find((o) => o.value === form.employment_status)?.label,
      title: "Are you currently employed?",
      problem: "Choose the answer that fits best.",
      body: <ChoiceTiles name="employment" options={EMPLOYMENT} value={form.employment_status} describedBy={errId} onChange={(v) => set("employment_status", v)} />,
    },
    {
      key: "age", label: "Your age", summary: () => form.age != null && String(form.age),
      title: "What is your age?",
      problem: "Enter an age from 0 to 120.",
      body: <NumberInput id="age" value={form.age} min={0} max={120} placeholder="For example, 34" describedBy={errId} invalid={showError} onChange={(v) => set("age", v)} />,
    },
    {
      key: "children", label: "Children",
      summary: () => (form.has_children === false ? "None" : form.children_ages.length ? `Ages ${form.children_ages.filter((a) => a != null).join(", ")}` : null),
      title: "Do you have children under 19 in your household?",
      problem: "Answer yes or no. If yes, enter how many children and each child's age from 0 to 18.",
      body: (
        <>
          <ChoiceTiles
            name="has_children" options={YES_NO} value={form.has_children} describedBy={errId}
            onChange={(v) => update((f) => ({ ...f, has_children: v, child_count: v ? (f.child_count || 1) : null, children_ages: v ? Array.from({ length: f.child_count || 1 }, () => null) : [] }))}
          />
          {form.has_children && (
            <div className="mt-8 border-t border-divider pt-6">
              <label htmlFor="child-count" id="child-count-label" className="block font-semibold">How many children?</label>
              <NumberInput
                id="child-count" labelledBy="child-count-label" className="mt-2 max-w-40"
                value={form.child_count} min={1} max={10} placeholder="For example, 2"
                onChange={(v) => {
                  const count = v == null ? null : Math.min(Math.max(v, 1), 10);
                  update((f) => ({ ...f, child_count: count, children_ages: Array.from({ length: count || 0 }, (_, i) => f.children_ages[i] ?? null) }));
                }}
              />
              {form.children_ages.length > 0 && (
                <fieldset className="mt-6">
                  <legend className="font-semibold">Their ages</legend>
                  <p className="text-muted">Use 0 for a baby under 1 year old.</p>
                  <div className="mt-3 flex flex-wrap gap-4">
                    {form.children_ages.map((age, i) => (
                      <label key={i} className="flex w-28 flex-col gap-1 font-semibold">
                        Child {i + 1}
                        <input
                          type="number" inputMode="numeric" min={0} max={18} value={age ?? ""}
                          aria-invalid={showError && !isInt(age, 0, 18) ? "true" : undefined}
                          onChange={(e) => {
                            const ages = [...form.children_ages];
                            ages[i] = e.target.value === "" ? null : Number(e.target.value);
                            set("children_ages", ages);
                          }}
                          className="input font-normal tabular-nums"
                        />
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}
            </div>
          )}
        </>
      ),
    },
    {
      key: "is_pregnant", label: "Pregnancy", summary: () => yesNo(form.is_pregnant),
      title: "Is anyone in your household pregnant?",
      problem: "Answer yes or no.",
      body: <ChoiceTiles name="pregnant" options={YES_NO} value={form.is_pregnant} describedBy={errId} onChange={(v) => set("is_pregnant", v)} />,
    },
    {
      key: "disability", label: "Disability", summary: () => yesNo(form.has_disability),
      title: "Does anyone in your household have a disability?",
      problem: "Answer yes or no. If yes, also say whether that person already receives disability benefits.",
      body: (
        <>
          <ChoiceTiles
            name="disability" options={YES_NO} value={form.has_disability} describedBy={errId}
            onChange={(v) => update((f) => ({ ...f, has_disability: v, receiving_disability_benefits: null }))}
          />
          {form.has_disability && (
            <div className="mt-8 border-t border-divider pt-6">
              <p id="disability-benefits-label" className="font-semibold">Is that person already receiving disability benefits?</p>
              <ChoiceTiles name="disability_benefits" labelledBy="disability-benefits-label" options={YES_NO} value={form.receiving_disability_benefits} onChange={(v) => set("receiving_disability_benefits", v)} />
            </div>
          )}
        </>
      ),
    },
    {
      key: "insurance_status", label: "Insurance", summary: () => INSURANCE.find((o) => o.value === form.insurance_status)?.label,
      title: "What is your current health insurance situation?",
      problem: "Choose the answer that fits best.",
      body: <ChoiceTiles name="insurance" options={INSURANCE} value={form.insurance_status} describedBy={errId} onChange={(v) => set("insurance_status", v)} />,
    },
    {
      key: "citizenship", label: "Citizenship", summary: () => CITIZENSHIP.find((o) => o.value === form.citizenship)?.label,
      title: "Are you a US citizen or legal permanent resident?",
      hint: "Some programs are open regardless of your answer, and we check those too.",
      problem: "Choose an answer. You can select Prefer not to say.",
      body: <ChoiceTiles name="citizenship" options={CITIZENSHIP} value={form.citizenship} describedBy={errId} onChange={(v) => set("citizenship", v)} />,
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;
  const valid = (i) => RULES[i](form);
  // A question can be revisited once reached, as long as every earlier answer is still valid.
  const canJump = (i) => i <= furthest && RULES.slice(0, i).every((r) => r(form));

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await matchBenefits(toProfile(form));
      saveAnswers(scope, form, { complete: true });
      saveResults(scope, result);
      navigate("/matches");
    } catch {
      setError("We couldn't reach the benefits checker. Check your connection and select See my benefits again.");
      setSubmitting(false);
    }
  }

  function startOver() {
    clearAnswers(scope);
    dirty.current = false;
    setForm(INITIAL);
    setStep(0);
    setFurthest(0);
    setRestored(false);
  }

  return (
    <div className="container-page grid gap-10 py-8 lg:grid-cols-[19rem_1fr] lg:gap-14 lg:py-12">
      <aside aria-label="Your answers" className="hidden self-start rounded-lg border border-border bg-surface-alt p-5 lg:sticky lg:top-6 lg:block">
        <h2 className="text-xl">Your answers</h2>
        <p className="mt-1 text-sm text-muted">Select an answered question to change it.</p>
        <ol className="mt-4 space-y-0.5">
          {steps.map((st, i) => {
            const answer = i < step || (i <= furthest && valid(i)) ? st.summary() : null;
            const isCurrent = i === step;
            const jump = canJump(i) && !isCurrent && !submitting;
            return (
              <li key={st.key}>
                <button
                  type="button" disabled={!jump} onClick={() => setStep(i)} aria-current={isCurrent ? "step" : undefined}
                  className={`flex w-full items-start gap-3 border-l-4 px-3 py-2 text-left disabled:cursor-default ${isCurrent ? "border-accent bg-white" : "border-transparent"} ${jump ? "hover:bg-white" : ""}`}
                >
                  <span className="w-5 shrink-0 pt-0.5 text-sm font-bold tabular-nums">{answer ? <Icon name="check" className="h-4 w-4" /> : i + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold">{st.label}</span>
                    {answer && <span className="block truncate text-sm text-muted">{answer}</span>}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </aside>

      <div className="max-w-2xl">
        {restored && (
          <Alert variant="info" title="We filled in your saved answers" className="mb-8">
            <p>Change anything you need, then go to the last question and select See my benefits to check again.</p>
            <p><Button variant="secondary" className="mt-3" onClick={startOver}>Start over</Button></p>
          </Alert>
        )}
        <p className="font-semibold tabular-nums" aria-live="polite">Question {step + 1} of {steps.length}</p>
        <div className="mt-2 flex gap-1 lg:hidden" aria-hidden="true">
          {steps.map((st, i) => <span key={st.key} className={`h-2 flex-1 ${i <= step ? "bg-primary-dark" : "bg-divider"}`} />)}
        </div>

        <form
          noValidate className="mt-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (submitting) return;
            if (!valid(step)) { setShowError(true); return; }
            if (isLast) submit(); else setStep((s) => s + 1);
          }}
        >
          <div key={current.key} className="animate-settle">
            <h1 id="question-title" ref={titleRef} tabIndex={-1} className="outline-none">{current.title}</h1>
            {current.hint && <p id="question-hint" className="mt-3 max-w-[55ch] text-lg text-muted">{current.hint}</p>}
            {showError && (
              <p id="question-error" role="alert" className="mt-4 border-l-4 border-error pl-3 font-semibold text-error">
                <span className="sr-only">Error: </span>{current.problem}
              </p>
            )}
            {current.body}
          </div>

          {error && <Alert variant="error" className="mt-6"><p>{error}</p></Alert>}

          <div className="mt-10 flex items-center justify-between gap-3">
            <Button variant="secondary" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || submitting} className={step === 0 ? "invisible" : ""}>
              <Icon name="arrowLeft" /> Back
            </Button>
            <Button type="submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? "Checking programs..." : isLast ? <>See my benefits <Icon name="arrowRight" /></> : <>Next <Icon name="arrowRight" /></>}
            </Button>
          </div>
        </form>
      </div>
      {submitting && <LoadingScreen />}
    </div>
  );
}
