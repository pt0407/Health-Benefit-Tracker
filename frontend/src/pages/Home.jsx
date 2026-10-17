import { useAuth } from "../auth/AuthContext.jsx";
import DotGrid from "../components/brand/DotGrid.jsx";
import Icon from "../components/shared/Icon.jsx";
import { LinkButton } from "../components/ui/index.jsx";
import { usePageTitle } from "../lib/usePageTitle.js";

// What Civis checks, from data/programs/*.json (51 records).
const COVERAGE = [
  ["Food", "basket", ["SNAP", "WIC", "School lunch", "School Breakfast Program", "Summer meals for kids", "Senior meals", "Commodity Supplemental Food Program"]],
  [
    "Health coverage",
    "heart",
    [
      "Medicaid", "Children's Medicaid", "CHIP", "CHIP Perinatal", "Medicaid for Pregnant Women",
      "Medicaid for Parents and Caretakers", "Emergency Medicaid",
      "Medicaid for the Elderly and People with Disabilities", "Medicaid Buy-In for Adults",
      "Medicare", "Medicare Extra Help", "Medicare Savings Programs", "Texas Benefits Counseling",
      "Primary Health Care Program", "Community health centers", "Title X family planning",
      "Texas Family Planning Program", "Texas Nurse-Family Partnership", "Texas Vaccines for Children",
    ],
  ],
  [
    "Cash help",
    "wallet",
    [
      "TANF", "Social Security retirement", "Earned Income Tax Credit", "Child Tax Credit",
      "Free tax help (VITA)", "Child and Dependent Care Credit", "Credit for Other Dependents", "Child support services",
    ],
  ],
  ["Utilities", "bolt", ["LIHEAP energy bill help", "Weatherization assistance", "Lifeline phone and internet"]],
  ["Work and unemployment", "briefcase", ["Unemployment benefits", "Child care scholarships", "Senior community service jobs", "Job Corps"]],
  [
    "Disability",
    "shield",
    ["SSDI", "SSI", "Vocational rehabilitation", "Ticket to Work", "Work Incentives Planning", "Independent Living Services"],
  ],
  ["Education and child care", "book", ["Head Start", "Early Head Start", "Texas Pre-K"]],
  ["Legal help", "scale", ["Free civil legal aid"]],
];

// Real output for one household from a local run of the matcher.
const EXAMPLE = [
  { name: "SNAP", detail: "Possible match", value: "Est. $349/mo" },
  { name: "LIHEAP", detail: "Strong match", value: "Est. $146/mo" },
  { name: "CHIP, for 2 children", detail: "Strong match", value: "Health coverage" },
];

const STEPS = [
  ["Answer 10 questions", "Household, income, ages and a few yes or no questions."],
  ["See your matches", "Sorted by estimated value, with the reason for each. Filter by type, level or time."],
  ["Track what you apply for", "Keep status, dates and documents for each program. Needs an account."],
];

export default function Home() {
  usePageTitle("");
  const { user } = useAuth();
  return (
    <>
      <section className="relative overflow-hidden bg-primary-dark text-white">
        <DotGrid className="pointer-events-none absolute inset-0" />
        <div className="container-page relative grid gap-12 py-14 lg:grid-cols-[1.15fr_1fr] lg:items-center lg:py-20">
          <div>
            <h1 className="max-w-[18ch] text-4xl text-white md:text-6xl">
              Find out which benefits your household may qualify for
            </h1>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <LinkButton to="/quiz" variant="gold" className="sm:min-w-44">Take the quiz</LinkButton>
              {user ? (
                <LinkButton to="/tracker" variant="light">Go to your tracker</LinkButton>
              ) : (
                <LinkButton to="/signin" variant="light">Sign in</LinkButton>
              )}
            </div>
          </div>

          <figure className="panel overflow-hidden bg-white text-ink">
            <figcaption className="bg-accent px-6 py-3 font-bold text-primary-dark">
              Example: a family of 4 in Texas earning about $22,500
            </figcaption>
            <div className="p-6">
              <p className="text-2xl font-bold">6 programs may fit</p>
              <ul className="mt-4 divide-y divide-divider border-y border-divider">
                {EXAMPLE.map((p) => (
                  <li key={p.name} className="flex items-center justify-between gap-4 py-3">
                    <div>
                      <p className="font-bold">{p.name}</p>
                      <p className="text-muted">{p.detail}</p>
                    </div>
                    <p className="shrink-0 font-semibold tabular-nums">{p.value}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-muted">Example only. Dollar amounts are estimates.</p>
            </div>
          </figure>
        </div>
      </section>

      <section className="container-page py-14" aria-labelledby="checks-title">
        <h2 id="checks-title">What Civis checks</h2>
        <table className="mt-5 w-full border-collapse text-left">
          <caption className="sr-only">Programs Civis checks, grouped by type</caption>
          <thead>
            <tr className="border-b-2 border-ink">
              <th scope="col" className="w-2/5 py-2 pr-4 font-bold md:w-1/3">Type of help</th>
              <th scope="col" className="py-2 font-bold">Programs</th>
            </tr>
          </thead>
          <tbody>
            {COVERAGE.map(([type, icon, programs]) => (
              <tr key={type} className="border-b border-divider align-top">
                <th scope="row" className="py-3 pr-4 font-bold">
                  <span className="flex items-start gap-2.5 text-primary-dark">
                    <Icon name={icon} className="mt-0.5 h-5 w-5" />
                    <span className="text-ink">{type}</span>
                  </span>
                </th>
                <td className="py-3">{programs.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="border-y border-divider bg-surface-alt" aria-labelledby="how-title">
        <div className="container-page py-14">
          <h2 id="how-title">How it works</h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-3">
            {STEPS.map(([title, text], i) => (
              <li key={title} className="flex gap-4 md:block">
                <span
                  aria-hidden="true"
                  className="num-badge flex h-12 w-12 shrink-0 items-center justify-center bg-primary-dark text-2xl font-extrabold text-white"
                >
                  {i + 1}
                </span>
                <div className="md:mt-4">
                  <h3>{title}</h3>
                  <p className="mt-2">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="container-page py-12" aria-labelledby="before-title">
        <div className="flex flex-col gap-5 rounded-lg border-l-8 border-accent bg-primary-lighter p-5 md:flex-row md:items-center md:justify-between md:p-6">
          <div>
            <h2 id="before-title" className="text-xl">Before you start</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Have your household size, rough income and children's ages ready.</li>
              <li>Civis estimates. Only the agency that runs a program decides who qualifies.</li>
              <li>Answers are saved in this browser and sent to Civis only to check programs.</li>
            </ul>
          </div>
          <LinkButton to="/quiz" className="shrink-0 md:min-w-44">Take the quiz</LinkButton>
        </div>
      </section>
    </>
  );
}
