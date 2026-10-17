// Quiz options, starting answers and a readable summary. The payload built by
// toProfile() must keep matching backend/models/user_profile.py exactly.

export const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
  "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
  "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
  "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
];

// Representative income for each bracket. The contract also carries the bracket
// label so the backend can tell an estimate from an exact figure.
export const INCOME_BRACKETS = [
  { value: "<15k", label: "Under $15,000", income: 10000 },
  { value: "15-30k", label: "$15,000 to $30,000", income: 22500 },
  { value: "30-50k", label: "$30,000 to $50,000", income: 40000 },
  { value: "50-75k", label: "$50,000 to $75,000", income: 62500 },
  { value: "75k+", label: "Over $75,000", income: 90000 },
];

export const EMPLOYMENT = [
  { value: "employed", label: "Employed" },
  { value: "unemployed", label: "Not working" },
  { value: "self_employed", label: "Self-employed" },
  { value: "recently_unemployed", label: "Recently lost my job" },
];

export const INSURANCE = [
  { value: "uninsured", label: "No insurance" },
  { value: "employer", label: "Through an employer" },
  { value: "marketplace", label: "Marketplace plan" },
  { value: "medicaid_medicare", label: "Medicaid or Medicare" },
  { value: "other", label: "Something else" },
];

export const CITIZENSHIP = [
  { value: "citizen", label: "Yes" },
  { value: "not_citizen", label: "No" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

export const INITIAL = {
  state: "TX",
  household_size: null,
  income_bracket: null,
  annual_income: null,
  employment_status: null,
  age: null,
  has_children: null,
  children_ages: [],
  child_count: null, // UI only: drives the per-child age inputs
  is_pregnant: null,
  has_disability: null,
  receiving_disability_benefits: null,
  insurance_status: null,
  citizenship: null,
};

// Merge saved answers over the defaults and rebuild the UI-only child count.
export function normalizeAnswers(saved) {
  const merged = { ...INITIAL, ...(saved || {}) };
  merged.children_ages = Array.isArray(merged.children_ages) ? merged.children_ages : [];
  if (merged.has_children && !merged.child_count) merged.child_count = merged.children_ages.length || 1;
  return merged;
}

export function toProfile(form) {
  const { child_count, ...rest } = form; // eslint-disable-line no-unused-vars
  return {
    ...rest,
    has_children: !!form.has_children,
    children_ages: form.children_ages.filter((a) => a != null),
  };
}

const labelOf = (list, value) => list.find((o) => o.value === value)?.label;
const yesNo = (v) => (v == null ? null : v ? "Yes" : "No");

// Readable list of what has been answered, used on the quiz, matches and tracker.
export function summarizeAnswers(a) {
  if (!a) return [];
  const rows = [
    ["State", a.state],
    ["Household", a.household_size ? `${a.household_size} ${a.household_size === 1 ? "person" : "people"}` : null],
    ["Income", labelOf(INCOME_BRACKETS, a.income_bracket)],
    ["Work", labelOf(EMPLOYMENT, a.employment_status)],
    ["Your age", a.age != null ? String(a.age) : null],
    [
      "Children",
      a.has_children === false
        ? "None"
        : a.children_ages?.filter((x) => x != null).length
          ? `Ages ${a.children_ages.filter((x) => x != null).join(", ")}`
          : null,
    ],
    ["Pregnancy", yesNo(a.is_pregnant)],
    ["Disability", yesNo(a.has_disability)],
    ["Insurance", labelOf(INSURANCE, a.insurance_status)],
    ["Citizen or permanent resident", labelOf(CITIZENSHIP, a.citizenship)],
  ];
  return rows.filter(([, value]) => value).map(([label, value]) => ({ label, value }));
}
