// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 2.
// On submit, POST the quiz answers (UserProfile shape) and navigate to
// /results with the response, e.g. navigate("/results", { state: result }).

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { matchBenefits } from "../../api/benefitsApi.js";

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

function OptionButtons({ options, value, onChange }) {
  return (
    <div className="mt-4 flex flex-col gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`rounded-lg border px-4 py-3 text-left font-medium transition
            ${value === o.value
              ? "border-blue-600 bg-blue-50 text-blue-700"
              : "border-gray-300 bg-white hover:border-blue-400"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function NumberInput({ value, onChange, min, max, placeholder }) {
  return (
    <input
      type="number"
      min={min}
      max={max}
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className="mt-4 w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:border-blue-500 focus:outline-none"
    />
  );
}

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
  const [form, setForm] = useState(INITIAL);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const steps = [
    {
      key: "state",
      title: "What state do you live in?",
      valid: () => !!form.state,
      body: (
        <select
          value={form.state}
          onChange={(e) => set("state", e.target.value)}
          className="mt-4 w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:border-blue-500 focus:outline-none"
        >
          {US_STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      ),
    },
    {
      key: "household_size",
      title: "How many people live in your household?",
      hint: "Include yourself, your spouse, and anyone you support.",
      valid: () => Number.isInteger(form.household_size) && form.household_size >= 1 && form.household_size <= 20,
      body: <NumberInput value={form.household_size} min={1} max={20} placeholder="e.g. 4"
                         onChange={(v) => set("household_size", v)} />,
    },
    {
      key: "income",
      title: "What is your approximate annual household income?",
      hint: "Before taxes, for everyone in the household combined.",
      valid: () => form.income_bracket != null,
      body: (
        <div className="mt-4 flex flex-col gap-2">
          {INCOME_BRACKETS.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => setForm((f) => ({ ...f, income_bracket: b.value, annual_income: b.income }))}
              className={`rounded-lg border px-4 py-3 text-left font-medium transition
                ${form.income_bracket === b.value
                  ? "border-blue-600 bg-blue-50 text-blue-700"
                  : "border-gray-300 bg-white hover:border-blue-400"}`}
            >
              {b.label}
            </button>
          ))}
        </div>
      ),
    },
    {
      key: "employment_status",
      title: "Are you currently employed?",
      valid: () => !!form.employment_status,
      body: <OptionButtons options={EMPLOYMENT} value={form.employment_status}
                           onChange={(v) => set("employment_status", v)} />,
    },
    {
      key: "age",
      title: "What is your age?",
      valid: () => Number.isInteger(form.age) && form.age >= 0 && form.age <= 120,
      body: <NumberInput value={form.age} min={0} max={120} placeholder="e.g. 34"
                         onChange={(v) => set("age", v)} />,
    },
    {
      key: "children",
      title: "Do you have children under 19 in your household?",
      valid: () =>
        form.has_children === false ||
        (form.has_children === true && form.children_ages.length >= 1 &&
          form.children_ages.every((a) => Number.isInteger(a) && a >= 0 && a <= 19)),
      body: (
        <>
          <OptionButtons
            options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
            value={form.has_children}
            onChange={(v) =>
              setForm((f) => ({ ...f, has_children: v, child_count: v ? (f.child_count || 1) : null, children_ages: [] }))}
          />
          {form.has_children && (
            <div className="mt-4">
              <label className="text-sm text-gray-600">How many, and their ages</label>
              <NumberInput
                value={form.child_count} min={1} max={10} placeholder="number of children"
                onChange={(v) => {
                  const count = v == null ? null : Math.min(Math.max(v, 1), 10);
                  setForm((f) => ({
                    ...f,
                    child_count: count,
                    children_ages: Array.from({ length: count || 0 }, (_, i) => f.children_ages[i] ?? null),
                  }));
                }}
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {form.children_ages.map((age, i) => (
                  <input
                    key={i}
                    type="number"
                    min={0}
                    max={19}
                    value={age ?? ""}
                    placeholder={`Child ${i + 1} age`}
                    onChange={(e) => {
                      const ages = [...form.children_ages];
                      ages[i] = e.target.value === "" ? null : Number(e.target.value);
                      set("children_ages", ages);
                    }}
                    className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                  />
                ))}
              </div>
            </div>
          )}
        </>
      ),
    },
    {
      key: "is_pregnant",
      title: "Is anyone in your household pregnant?",
      valid: () => form.is_pregnant != null,
      body: <OptionButtons options={[{ value: true, label: "Yes" }, { value: false, label: "No" }]}
                           value={form.is_pregnant} onChange={(v) => set("is_pregnant", v)} />,
    },
    {
      key: "disability",
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
            <div className="mt-4">
              <label className="text-sm text-gray-600">Already receiving disability benefits?</label>
              <OptionButtons
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
      title: "What is your current health insurance situation?",
      valid: () => !!form.insurance_status,
      body: <OptionButtons options={INSURANCE} value={form.insurance_status}
                           onChange={(v) => set("insurance_status", v)} />,
    },
    {
      key: "citizenship",
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
      setError("Something went wrong checking your benefits. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-12">
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-500">
          <span>Question {step + 1} of {steps.length}</span>
        </div>
        <div className="mt-1 h-2 rounded-full bg-gray-200">
          <div
            className="h-2 rounded-full bg-blue-600 transition-all"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>

      <h2 className="text-2xl font-bold">{current.title}</h2>
      {current.hint && <p className="mt-1 text-gray-500">{current.hint}</p>}
      {current.body}

      {error && <p className="mt-4 text-red-600">{error}</p>}

      <div className="mt-8 flex justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 0 || submitting}
          className="rounded-lg px-5 py-2.5 font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-30"
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => (isLast ? submit() : setStep((s) => s + 1))}
          disabled={!current.valid() || submitting}
          className="rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {submitting ? "Checking…" : isLast ? "See my benefits" : "Next"}
        </button>
      </div>
    </main>
  );
}
