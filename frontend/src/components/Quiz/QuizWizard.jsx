// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 2.
// On submit, POST the quiz answers (UserProfile shape) and navigate to
// /results with the response, e.g. navigate("/results", { state: result }).

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { matchBenefits } from "../../api/benefitsApi.js";
import Icon from "../shared/Icon.jsx";

const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
  "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
  "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
  "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
];

// Representative income for each bracket (midpoint-ish). The contract also
// carries the bracket label so the backend can tell an estimate from an exact figure.
const INCOME_BRACKETS = [
  { value: "<15k", label: "Under $15,000", income: 10000 },
  { value: "15-30k", label: "$15,000 – $30,000", income: 22500 },
  { value: "30-50k", label: "$30,000 – $50,000", income: 40000 },
  { value: "50-75k", label: "$50,000 – $75,000", income: 62500 },
  { value: "75k+", label: "Over $75,000", income: 90000 },
];

const EMPLOYMENT = [
  { value: "employed", label: "Employed" },
  { value: "unemployed", label: "Not working" },
  { value: "self_employed", label: "Self-employed" },
  { value: "recently_unemployed", label: "Recently lost my job" },
];

const INSURANCE = [
  { value: "uninsured", label: "No insurance" },
  { value: "employer", label: "Through an employer" },
  { value: "marketplace", label: "Marketplace plan" },
  { value: "medicaid_medicare", label: "Medicaid or Medicare" },
  { value: "other", label: "Something else" },
];

const CITIZENSHIP = [
  { value: "citizen", label: "Yes" },
  { value: "not_citizen", label: "No" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

const FIELD = "w-full rounded-2xl border-2 border-line bg-surface px-5 py-3.5 text-xl font-semibold text-ink " +
  "shadow-[var(--shadow-card)] transition-colors placeholder:font-normal placeholder:text-subtle hover:border-brand-200 focus:border-brand-700";

function OptionButtons({ options, value, onChange, labelledBy = "question-title" }) {
  return (
    <div role="group" aria-labelledby={labelledBy} className="mt-6 flex flex-col gap-2.5">
      {options.map((o) => {
        const selected = value === o.value;
        return (
          <button
            key={String(o.value)}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(o.value)}
            className={`flex min-h-15 items-center justify-between gap-3 rounded-2xl border-2 px-5 py-3 text-left text-lg font-semibold transition
              ${selected
                ? "border-brand-700 bg-brand-50 text-brand-900"
                : "border-transparent bg-surface text-ink shadow-[var(--shadow-card)] hover:-translate-y-px hover:border-brand-200"}`}
          >
            {o.label}
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full border-2 transition-colors
                ${selected ? "border-brand-700 bg-brand-700 text-white" : "border-line-strong bg-surface"}`}
            >
              {selected && <Icon name="check" className="h-3.5 w-3.5" />}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function NumberInput({ value, onChange, min, max, placeholder, id, labelledBy = "question-title", describedBy, className = "mt-6" }) {
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
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className={`${FIELD} tabular-nums ${className}`}
    />
  );
}

const yesNo = (v) => (v == null ? null : v ? "Yes" : "No");

const INITIAL = {
  state: "TX",
  household_size: null,
  income_bracket: null,
  annual_income: null,
  employment_status: null,
  age: null,
  has_children: null,
  children_ages: [],
  child_count: null, // UI-only: drives the per-child age inputs
  is_pregnant: null,
  has_disability: null,
  receiving_disability_benefits: null,
  insurance_status: null,
  citizenship: null,
};

export default function QuizWizard() {
  const [step, setStep] = useState(0);
  const [furthest, setFurthest] = useState(0);
  const [form, setForm] = useState(INITIAL);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const titleRef = useRef(null);
  const firstRender = useRef(true);

  // Move focus to each new question so screen readers announce it.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    titleRef.current?.focus();
    setFurthest((f) => Math.max(f, step));
  }, [step]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const steps = [
    {
      key: "state",
      label: "State",
      summary: () => form.state,
      title: "What state do you live in?",
      hint: "We check federal programs everywhere and Texas state programs in Texas.",
      valid: () => !!form.state,
      body: (
        <select
          value={form.state}
          aria-labelledby="question-title"
          onChange={(e) => set("state", e.target.value)}
          className={`${FIELD} mt-6`}
        >
          {US_STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      ),
    },
    {
      key: "household_size",
      label: "Household",
      summary: () => form.household_size && `${form.household_size} ${form.household_size === 1 ? "person" : "people"}`,
      title: "How many people live in your household?",
      hint: "Include yourself, your spouse, and anyone you support.",
      valid: () => Number.isInteger(form.household_size) && form.household_size >= 1 && form.household_size <= 20,
      body: <NumberInput value={form.household_size} min={1} max={20} placeholder="e.g. 4"
                         onChange={(v) => set("household_size", v)} />,
    },
    {
      key: "income",
      label: "Income",
      summary: () => INCOME_BRACKETS.find((b) => b.value === form.income_bracket)?.label,
      title: "What is your approximate annual household income?",
      hint: "Before taxes, for everyone in the household combined.",
      valid: () => form.income_bracket != null,
      body: (
        <OptionButtons
          options={INCOME_BRACKETS}
          value={form.income_bracket}
          onChange={(v) => {
            const b = INCOME_BRACKETS.find((x) => x.value === v);
            setForm((f) => ({ ...f, income_bracket: b.value, annual_income: b.income }));
          }}
        />
      ),
    },
    {
      key: "employment_status",
      label: "Work",
      summary: () => EMPLOYMENT.find((o) => o.value === form.employment_status)?.label,
      title: "Are you currently employed?",
      valid: () => !!form.employment_status,
      body: <OptionButtons options={EMPLOYMENT} value={form.employment_status}
                           onChange={(v) => set("employment_status", v)} />,
    },
    {
      key: "age",
      label: "Your age",
      summary: () => form.age != null && String(form.age),
      title: "What is your age?",
      valid: () => Number.isInteger(form.age) && form.age >= 0 && form.age <= 120,
      body: <NumberInput value={form.age} min={0} max={120} placeholder="e.g. 34"
                         onChange={(v) => set("age", v)} />,
    },
    {
      key: "children",
      label: "Children",
      summary: () => form.has_children === false ? "None" : form.children_ages.length ? `Ages ${form.children_ages.filter((a) => a != null).join(", ")}` : null,
      title: "Do you have children under 19 in your household?",
      valid: () =>
        form.has_children === false ||
        (form.has_children === true && form.children_ages.length >= 1 &&
          form.children_ages.every((a) => Number.isInteger(a) && a >= 0 && a <= 18)),
      body: (
        <>
          <OptionButtons
            options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
            value={form.has_children}
            onChange={(v) =>
              setForm((f) => ({ ...f, has_children: v, child_count: v ? (f.child_count || 1) : null, children_ages: [] }))}
          />
          {form.has_children && (
            <div className="mt-8 border-t border-line pt-6">
              <label htmlFor="child-count" id="child-count-label" className="block font-semibold text-ink">
                How many children?
              </label>
              <NumberInput
                id="child-count" labelledBy="child-count-label" className="mt-2 max-w-40"
                value={form.child_count} min={1} max={10} placeholder="e.g. 2"
                onChange={(v) => {
                  const count = v == null ? null : Math.min(Math.max(v, 1), 10);
                  setForm((f) => ({
                    ...f,
                    child_count: count,
                    children_ages: Array.from({ length: count || 0 }, (_, i) => f.children_ages[i] ?? null),
                  }));
                }}
              />
              {form.children_ages.length > 0 && (
                <fieldset className="mt-6">
                  <legend className="font-semibold text-ink">Their ages</legend>
                  <p className="text-muted">Use 0 for a baby under 1 year old.</p>
                  <div className="mt-3 flex flex-wrap gap-3">
                    {form.children_ages.map((age, i) => (
                      <label key={i} className="flex w-28 flex-col gap-1 text-sm font-medium text-muted">
                        Child {i + 1}
                        <input
                          type="number"
                          inputMode="numeric"
                          min={0}
                          max={18}
                          value={age ?? ""}
                          placeholder="Age"
                          onChange={(e) => {
                            const ages = [...form.children_ages];
                            ages[i] = e.target.value === "" ? null : Number(e.target.value);
                            set("children_ages", ages);
                          }}
                          className={`${FIELD} px-3 py-2.5 text-lg tabular-nums`}
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
      key: "is_pregnant",
      label: "Pregnancy",
      summary: () => yesNo(form.is_pregnant),
      title: "Is anyone in your household pregnant?",
      valid: () => form.is_pregnant != null,
      body: <OptionButtons options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
                           value={form.is_pregnant} onChange={(v) => set("is_pregnant", v)} />,
    },
    {
      key: "disability",
      label: "Disability",
      summary: () => yesNo(form.has_disability),
      title: "Does anyone in your household have a disability?",
      valid: () => form.has_disability === false ||
        (form.has_disability === true && form.receiving_disability_benefits != null),
      body: (
        <>
          <OptionButtons
            options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
            value={form.has_disability}
            onChange={(v) => setForm((f) => ({ ...f, has_disability: v, receiving_disability_benefits: null }))}
          />
          {form.has_disability && (
            <div className="mt-8 border-t border-line pt-6">
              <p id="disability-benefits-label" className="font-semibold text-ink">
                Is that person already receiving disability benefits?
              </p>
              <OptionButtons
                labelledBy="disability-benefits-label"
                options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
                value={form.receiving_disability_benefits}
                onChange={(v) => set("receiving_disability_benefits", v)}
              />
            </div>
          )}
        </>
      ),
    },
    {
      key: "insurance_status",
      label: "Insurance",
      summary: () => INSURANCE.find((o) => o.value === form.insurance_status)?.label,
      title: "What is your current health insurance situation?",
      valid: () => !!form.insurance_status,
      body: <OptionButtons options={INSURANCE} value={form.insurance_status}
                           onChange={(v) => set("insurance_status", v)} />,
    },
    {
      key: "citizenship",
      label: "Citizenship",
      summary: () => CITIZENSHIP.find((o) => o.value === form.citizenship)?.label,
      title: "Are you a US citizen or legal permanent resident?",
      hint: "Some programs are open regardless of your answer — we check those too.",
      valid: () => !!form.citizenship,
      body: <OptionButtons options={CITIZENSHIP} value={form.citizenship}
                           onChange={(v) => set("citizenship", v)} />,
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;

  async function submit() {
    setSubmitting(true);
    setError(null);
    const { child_count, ...rest } = form;
    const profile = { ...rest, has_children: !!form.has_children, children_ages: form.children_ages.filter((a) => a != null) };
    try {
      const result = await matchBenefits(profile);
      navigate("/results", { state: { result, profile } });
    } catch {
      setError("We couldn't reach the benefits checker. Check your connection and press See my benefits again.");
      setSubmitting(false);
    }
  }

  // A question can be revisited once reached, as long as every earlier answer is still valid.
  const canJump = (i) => i <= furthest && steps.slice(0, i).every((st) => st.valid());

  return (
    <main className="mx-auto grid max-w-6xl gap-10 px-4 pt-6 pb-16 sm:px-6 sm:pt-10 lg:grid-cols-[19rem_1fr] lg:gap-16">
      <aside className="on-brand hidden self-start rounded-3xl bg-brand-900 p-6 text-cream lg:sticky lg:top-6 lg:block">
        <p className="font-display text-2xl font-semibold">Your answers</p>
        <p className="mt-1 text-sm text-on-brand-muted">Select any answered question to change it.</p>
        <ol className="mt-5 space-y-0.5">
          {steps.map((st, i) => {
            const answer = i < step || (i <= furthest && st.valid()) ? st.summary() : null;
            const isCurrent = i === step;
            const jump = canJump(i) && !isCurrent && !submitting;
            return (
              <li key={st.key}>
                <button
                  type="button"
                  disabled={!jump}
                  onClick={() => setStep(i)}
                  aria-current={isCurrent ? "step" : undefined}
                  className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left transition-colors
                    ${isCurrent ? "bg-brand-800" : ""} ${jump ? "hover:bg-brand-800" : "cursor-default"}`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold tabular-nums
                      ${answer ? "bg-accent text-brand-950" : isCurrent ? "bg-cream text-brand-950" : "border border-on-brand-muted/50 text-on-brand-muted"}`}
                  >
                    {answer ? <Icon name="check" className="h-3.5 w-3.5" /> : i + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className={`block text-sm font-semibold ${isCurrent || answer ? "text-cream" : "text-on-brand-muted"}`}>
                      {st.label}
                    </span>
                    {answer && <span className="block truncate text-sm text-on-brand-muted">{answer}</span>}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </aside>

      <div className="max-w-2xl">
        <div className="lg:hidden">
          <p className="text-sm font-semibold text-muted tabular-nums" aria-live="polite">
            Question {step + 1} of {steps.length} · {current.label}
          </p>
          <div className="mt-2.5 flex gap-1" aria-hidden="true">
            {steps.map((st, i) => (
              <span key={st.key} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-brand-700" : "bg-line"}`} />
            ))}
          </div>
        </div>
        <p className="hidden text-sm font-semibold text-muted tabular-nums lg:block" aria-live="polite">
          Question {step + 1} of {steps.length}
        </p>

        <form
          className="mt-8 lg:mt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!current.valid() || submitting) return;
            isLast ? submit() : setStep((s) => s + 1);
          }}
        >
          <div key={current.key} className="animate-settle">
            <h1
              id="question-title"
              ref={titleRef}
              tabIndex={-1}
              className="font-display text-3xl font-semibold text-brand-900 outline-none sm:text-5xl"
            >
              {current.title}
            </h1>
            {current.hint && <p id="question-hint" className="mt-3 max-w-[55ch] text-lg text-muted">{current.hint}</p>}
            {current.body}
          </div>

          {error && (
            <div role="alert" className="mt-6 flex gap-3 rounded-2xl bg-danger-50 p-4 text-danger-700">
              <Icon name="alert" className="mt-0.5 h-5 w-5" />
              <p>{error}</p>
            </div>
          )}

          <div className="mt-10 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0 || submitting}
              className="inline-flex min-h-12 items-center gap-2 rounded-2xl px-4 font-semibold text-muted transition-colors hover:bg-brand-50 hover:text-brand-900 disabled:invisible"
            >
              <Icon name="arrowLeft" />
              Back
            </button>
            <button
              type="submit"
              disabled={!current.valid() || submitting}
              aria-busy={submitting}
              className="inline-flex min-h-14 items-center gap-2 rounded-2xl bg-brand-900 px-7 text-lg font-semibold text-cream shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:bg-brand-800 disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-line disabled:text-subtle disabled:shadow-none"
            >
              {submitting ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-cream/40 border-t-cream" aria-hidden="true" />
                  Checking programs…
                </>
              ) : isLast ? (
                <>See my benefits <Icon name="arrowRight" /></>
              ) : (
                <>Next <Icon name="arrowRight" /></>
              )}
            </button>
          </div>
          <p className="mt-3 min-h-6 text-right text-sm text-muted" aria-live="polite">
            {submitting && "This can take up to a minute the first time."}
          </p>
        </form>
      </div>
    </main>
  );
}
