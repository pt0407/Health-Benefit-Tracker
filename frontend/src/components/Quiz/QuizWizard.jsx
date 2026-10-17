// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 2.
// On submit, POSTs the quiz answers (UserProfile shape) to POST /api/match
// and navigates to /results with the MatchResponse via router state.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { matchBenefits } from "../../api/benefitsApi.js";

// Steps: 0=location, 1=household, 2=income, 3=health, 4=citizenship
const TOTAL_STEPS = 5;

const EMPLOYMENT_OPTIONS = [
  { value: "employed", label: "Employed" },
  { value: "self_employed", label: "Self-employed" },
  { value: "recently_unemployed", label: "Recently unemployed (last 6 months)" },
  { value: "unemployed", label: "Not currently working" },
];

const INSURANCE_OPTIONS = [
  { value: "uninsured", label: "No insurance" },
  { value: "employer", label: "Employer coverage" },
  { value: "marketplace", label: "Marketplace / ACA plan" },
  { value: "medicaid_medicare", label: "Medicaid or Medicare" },
  { value: "other", label: "Other coverage" },
];

const INCOME_BRACKETS = [
  { value: "<15k", label: "Under $15,000" },
  { value: "15-30k", label: "$15,000 – $30,000" },
  { value: "30-50k", label: "$30,000 – $50,000" },
  { value: "50-75k", label: "$50,000 – $75,000" },
  { value: "75k+", label: "$75,000 or more" },
];

const BRACKET_MIDPOINTS = {
  "<15k": 7500,
  "15-30k": 22500,
  "30-50k": 40000,
  "50-75k": 62500,
  "75k+": 100000,
};

function StepIndicator({ current, total }) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-2">
        {Array.from({ length: total }).map((_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i <= current ? "bg-blue-600" : "bg-gray-200"
            }`}
          />
        ))}
      </div>
      <p className="text-sm text-gray-500">
        Step {current + 1} of {total}
      </p>
    </div>
  );
}

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="mt-1 text-sm text-red-600">{msg}</p>;
}

export default function QuizWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const [form, setForm] = useState({
    // Step 0 — location
    state: "TX",
    // Step 1 — household
    household_size: "",
    age: "",
    has_children: "",
    children_ages_raw: "", // free-text, parsed on submit
    is_pregnant: false,
    has_disability: false,
    receiving_disability_benefits: null,
    // Step 2 — income
    employment_status: "",
    income_bracket: "",
    // Step 3 — health
    insurance_status: "",
    // Step 4 — citizenship
    citizenship: "",
  });

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setFieldErrors((e) => ({ ...e, [field]: undefined }));
  }

  // ── Validation per step ────────────────────────────────────────────────────

  function validateStep(s) {
    const errs = {};
    if (s === 0) {
      if (!form.state || form.state.length !== 2)
        errs.state = "Please select a state.";
    }
    if (s === 1) {
      if (!form.household_size || Number(form.household_size) < 1)
        errs.household_size = "Enter a household size of at least 1.";
      if (form.age === "" || Number(form.age) < 0 || Number(form.age) > 120)
        errs.age = "Enter your age (0–120).";
      if (form.has_children === "")
        errs.has_children = "Please answer this question.";
      if (form.has_children === "yes" && form.children_ages_raw.trim() === "")
        errs.children_ages_raw = "Enter at least one child's age.";
    }
    if (s === 2) {
      if (!form.employment_status)
        errs.employment_status = "Please select an option.";
      if (!form.income_bracket)
        errs.income_bracket = "Please select an income range.";
    }
    if (s === 3) {
      if (!form.insurance_status)
        errs.insurance_status = "Please select an option.";
    }
    if (s === 4) {
      if (!form.citizenship)
        errs.citizenship = "Please select an option.";
    }
    return errs;
  }

  function next() {
    const errs = validateStep(step);
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }
    setStep((s) => s + 1);
  }

  function back() {
    setApiError(null);
    setStep((s) => s - 1);
  }

  // ── Build UserProfile payload ──────────────────────────────────────────────

  function buildProfile() {
    const children_ages =
      form.has_children === "yes"
        ? form.children_ages_raw
            .split(/[\s,]+/)
            .map(Number)
            .filter((n) => !isNaN(n) && n >= 0)
        : [];

    const annual_income = BRACKET_MIDPOINTS[form.income_bracket] ?? 0;

    return {
      state: form.state,
      household_size: Number(form.household_size),
      annual_income,
      income_bracket: form.income_bracket || null,
      employment_status: form.employment_status,
      age: Number(form.age),
      has_children: form.has_children === "yes",
      children_ages,
      is_pregnant: form.is_pregnant,
      has_disability: form.has_disability,
      receiving_disability_benefits: form.has_disability
        ? form.receiving_disability_benefits
        : null,
      insurance_status: form.insurance_status,
      // "citizen" covers US citizens AND legal permanent residents (per contract note)
      citizenship: form.citizenship,
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validateStep(step);
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }
    setSubmitting(true);
    setApiError(null);
    try {
      const profile = buildProfile();
      const result = await matchBenefits(profile);
      navigate("/results", { state: result });
    } catch (err) {
      setApiError(
        err?.response?.data?.detail ||
          "Something went wrong. Please try again."
      );
      setSubmitting(false);
    }
  }

  // ── Step renderers ─────────────────────────────────────────────────────────

  function renderStep0() {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold">Where do you live?</h2>
        <p className="text-gray-600">
          Benefit rules vary by state. We start with Texas — other states coming soon.
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            State
          </label>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.state}
            onChange={(e) => set("state", e.target.value)}
          >
            <option value="TX">Texas</option>
          </select>
          <FieldError msg={fieldErrors.state} />
        </div>
      </div>
    );
  }

  function renderStep1() {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold">Tell us about your household</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            How many people live in your household? (including yourself)
          </label>
          <input
            type="number"
            min="1"
            max="20"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.household_size}
            onChange={(e) => set("household_size", e.target.value)}
            placeholder="e.g. 4"
          />
          <FieldError msg={fieldErrors.household_size} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Your age
          </label>
          <input
            type="number"
            min="0"
            max="120"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.age}
            onChange={(e) => set("age", e.target.value)}
            placeholder="e.g. 34"
          />
          <FieldError msg={fieldErrors.age} />
        </div>

        <div>
          <p className="block text-sm font-medium text-gray-700 mb-2">
            Do you have children under 19 in your household?
          </p>
          <div className="flex gap-4">
            {["yes", "no"].map((v) => (
              <label key={v} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="has_children"
                  value={v}
                  checked={form.has_children === v}
                  onChange={() => set("has_children", v)}
                  className="accent-blue-600"
                />
                <span className="capitalize">{v}</span>
              </label>
            ))}
          </div>
          <FieldError msg={fieldErrors.has_children} />
        </div>

        {form.has_children === "yes" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ages of children (separated by commas or spaces)
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.children_ages_raw}
              onChange={(e) => set("children_ages_raw", e.target.value)}
              placeholder="e.g. 3, 7, 12"
            />
            <FieldError msg={fieldErrors.children_ages_raw} />
          </div>
        )}

        <div className="flex items-center gap-3">
          <input
            id="pregnant"
            type="checkbox"
            className="accent-blue-600 h-4 w-4"
            checked={form.is_pregnant}
            onChange={(e) => set("is_pregnant", e.target.checked)}
          />
          <label htmlFor="pregnant" className="text-sm text-gray-700 cursor-pointer">
            I am currently pregnant
          </label>
        </div>

        <div>
          <div className="flex items-center gap-3 mb-2">
            <input
              id="disability"
              type="checkbox"
              className="accent-blue-600 h-4 w-4"
              checked={form.has_disability}
              onChange={(e) => set("has_disability", e.target.checked)}
            />
            <label htmlFor="disability" className="text-sm text-gray-700 cursor-pointer">
              I have a disability
            </label>
          </div>
          {form.has_disability && (
            <div className="ml-7">
              <p className="text-sm text-gray-700 mb-2">
                Are you currently receiving disability benefits (SSI/SSDI)?
              </p>
              <div className="flex gap-4">
                {[
                  { v: true, label: "Yes" },
                  { v: false, label: "No" },
                ].map(({ v, label }) => (
                  <label key={label} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="receiving_disability_benefits"
                      checked={form.receiving_disability_benefits === v}
                      onChange={() => set("receiving_disability_benefits", v)}
                      className="accent-blue-600"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  function renderStep2() {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold">Income &amp; employment</h2>

        <div>
          <p className="block text-sm font-medium text-gray-700 mb-2">
            What best describes your current employment?
          </p>
          <div className="space-y-2">
            {EMPLOYMENT_OPTIONS.map(({ value, label }) => (
              <label key={value} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="employment_status"
                  value={value}
                  checked={form.employment_status === value}
                  onChange={() => set("employment_status", value)}
                  className="accent-blue-600"
                />
                <span className="text-sm text-gray-800">{label}</span>
              </label>
            ))}
          </div>
          <FieldError msg={fieldErrors.employment_status} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Approximate total household income (before taxes, per year)
          </label>
          <div className="space-y-2">
            {INCOME_BRACKETS.map(({ value, label }) => (
              <label key={value} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="income_bracket"
                  value={value}
                  checked={form.income_bracket === value}
                  onChange={() => set("income_bracket", value)}
                  className="accent-blue-600"
                />
                <span className="text-sm text-gray-800">{label}</span>
              </label>
            ))}
          </div>
          <FieldError msg={fieldErrors.income_bracket} />
        </div>
      </div>
    );
  }

  function renderStep3() {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold">Health coverage</h2>

        <div>
          <p className="block text-sm font-medium text-gray-700 mb-2">
            What is your current health insurance situation?
          </p>
          <div className="space-y-2">
            {INSURANCE_OPTIONS.map(({ value, label }) => (
              <label key={value} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="insurance_status"
                  value={value}
                  checked={form.insurance_status === value}
                  onChange={() => set("insurance_status", value)}
                  className="accent-blue-600"
                />
                <span className="text-sm text-gray-800">{label}</span>
              </label>
            ))}
          </div>
          <FieldError msg={fieldErrors.insurance_status} />
        </div>
      </div>
    );
  }

  function renderStep4() {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold">Citizenship &amp; immigration status</h2>
        <p className="text-gray-600 text-sm">
          Some programs are open to all residents; others require citizenship or a qualifying
          immigration status. We ask only to match you accurately.
        </p>

        <div className="space-y-2">
          {[
            {
              value: "citizen",
              label: "Yes — I am a U.S. citizen or legal permanent resident (green card holder)",
            },
            {
              value: "not_citizen",
              label: "No — I have a different immigration status",
            },
            {
              value: "prefer_not_to_say",
              label: "Prefer not to say",
            },
          ].map(({ value, label }) => (
            <label key={value} className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio"
                name="citizenship"
                value={value}
                checked={form.citizenship === value}
                onChange={() => set("citizenship", value)}
                className="accent-blue-600 mt-0.5"
              />
              <span className="text-sm text-gray-800">{label}</span>
            </label>
          ))}
        </div>
        <FieldError msg={fieldErrors.citizenship} />
      </div>
    );
  }

  const steps = [renderStep0, renderStep1, renderStep2, renderStep3, renderStep4];
  const isLast = step === TOTAL_STEPS - 1;

  return (
    <main className="mx-auto max-w-xl px-4 py-12">
      <StepIndicator current={step} total={TOTAL_STEPS} />

      <form onSubmit={isLast ? handleSubmit : (e) => { e.preventDefault(); next(); }}
            noValidate>
        {steps[step]()}

        {apiError && (
          <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {apiError}
          </div>
        )}

        <div className="mt-8 flex gap-3">
          {step > 0 && (
            <button
              type="button"
              onClick={back}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {submitting ? "Checking…" : isLast ? "See my results" : "Continue"}
          </button>
        </div>
      </form>
    </main>
  );
}
