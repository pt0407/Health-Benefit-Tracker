import { Link, Route, Routes } from "react-router-dom";
import QuizWizard from "./components/Quiz/QuizWizard.jsx";
import ResultsDashboard from "./components/Results/ResultsDashboard.jsx";
import ErrorBoundary from "./components/shared/ErrorBoundary.jsx";
import Icon from "./components/shared/Icon.jsx";

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-brand-900">
      <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-brand-900 text-accent">
        <Icon name="check" className="h-4.5 w-4.5" />
      </span>
      Civis
    </Link>
  );
}

function Layout({ children }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:font-semibold focus:text-brand-900"
      >
        Skip to content
      </a>
      <header className="border-b border-line/70 print:hidden">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <span className="hidden text-sm font-medium text-muted sm:block">Federal + Texas programs</span>
        </div>
      </header>
      <div id="main" className="flex-1">{children}</div>
      <footer className="border-t border-line print:hidden">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted sm:flex-row sm:justify-between sm:px-6">
          <p>Civis is not a government website.</p>
          <p className="max-w-[60ch]">
            Results are estimates from your answers. Only the agency that runs a program can decide
            if you qualify.
          </p>
        </div>
      </footer>
    </div>
  );
}

// What the app checks, from data/programs/*.json.
const COVERAGE = [
  { icon: "basket", title: "Food", programs: ["SNAP", "WIC"] },
  {
    icon: "heart",
    title: "Health care",
    programs: [
      "Medicaid", "Children's Medicaid", "CHIP", "Medicaid for Pregnant Women", "CHIP Perinatal",
      "Emergency Medicaid", "Medicaid for the Elderly and People with Disabilities", "Medicare Extra Help",
    ],
  },
  { icon: "wallet", title: "Cash help", programs: ["TANF", "SSDI"] },
  { icon: "bolt", title: "Utilities", programs: ["LIHEAP energy bill help"] },
  { icon: "briefcase", title: "Work", programs: ["Unemployment benefits"] },
];

// Real output for one household from a local run of the matcher.
const EXAMPLE = [
  { name: "SNAP", value: 349, strength: "Possible match" },
  { name: "LIHEAP", value: 146, strength: "Strong match" },
  { name: "CHIP for 2 children", value: null, strength: "Strong match" },
];

function ExamplePreview() {
  return (
    <figure className="relative mx-auto w-full max-w-md lg:mx-0">
      <div aria-hidden="true" className="absolute -inset-4 -rotate-2 rounded-[2rem] bg-brand-900 sm:-inset-6" />
      <div className="relative rounded-3xl bg-surface p-5 shadow-[var(--shadow-lift)] sm:p-6">
        <figcaption className="text-sm font-medium text-muted">
          Example: family of 4 in Texas earning about $22,500
        </figcaption>
        <p className="font-display mt-1 text-2xl font-semibold text-brand-900">6 programs may fit</p>
        <ul className="mt-4 space-y-2.5">
          {EXAMPLE.map((p) => (
            <li key={p.name} className="flex items-center justify-between gap-3 rounded-2xl bg-canvas px-4 py-3">
              <div>
                <p className="font-semibold text-ink">{p.name}</p>
                <p className="text-sm text-muted">{p.strength}</p>
              </div>
              <span className="shrink-0 rounded-full bg-accent-100 px-3 py-1 text-sm font-semibold text-warn-900 tabular-nums">
                {p.value ? `Est. $${p.value}/mo` : "Health coverage"}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 flex items-center gap-2 text-sm font-medium text-brand-700">
          <Icon name="list" className="h-4 w-4" />
          Each one comes with a step-by-step plan to apply
        </p>
      </div>
    </figure>
  );
}

function Home() {
  return (
    <main className="overflow-x-clip">
      <section className="mx-auto grid max-w-6xl items-center gap-16 px-4 pt-12 pb-20 sm:px-6 sm:pt-20 lg:grid-cols-[1.1fr_1fr] lg:pb-28">
        <div>
          <h1 className="font-display text-5xl font-semibold text-brand-900 sm:text-7xl">
            Find the benefits <em className="text-brand-700">you're owed.</em> In minutes.
          </h1>
          <p className="mt-6 max-w-[52ch] text-lg text-muted sm:text-xl">
            Answer 10 short questions about your household. We check 14 federal and Texas programs
            and show you what you may qualify for, with exactly how to apply.
          </p>
          <div className="mt-9 flex flex-col gap-4 sm:flex-row sm:items-center">
            <Link
              to="/quiz"
              className="inline-flex min-h-14 items-center justify-center gap-2 whitespace-nowrap rounded-2xl bg-brand-900 px-7 text-lg font-semibold text-cream shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:bg-brand-800"
            >
              Check what I qualify for
              <Icon name="arrowRight" />
            </Link>
            <p className="text-muted">Free · No sign-up · About 3 minutes</p>
          </div>
        </div>
        <ExamplePreview />
      </section>

      <section className="on-brand bg-brand-900 text-cream">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-[1fr_2fr]">
            <div>
              <h2 className="font-display text-4xl font-semibold">What we check</h2>
              <p className="mt-4 max-w-[40ch] text-on-brand-muted">
                Every program below has official rules we match your answers against. Your answers
                aren't saved anywhere.
              </p>
            </div>
            <dl className="grid gap-x-10 gap-y-7 sm:grid-cols-2">
              {COVERAGE.map((c) => (
                <div key={c.title} className={c.programs.length > 4 ? "sm:row-span-2" : ""}>
                  <dt className="flex items-center gap-2.5 text-lg font-bold">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-brand-950">
                      <Icon name={c.icon} className="h-5 w-5" />
                    </span>
                    {c.title}
                  </dt>
                  <dd className="mt-2 pl-[2.875rem] text-on-brand-muted">{c.programs.join(" · ")}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <h2 className="font-display text-4xl font-semibold text-brand-900">How it works</h2>
        <ol className="mt-10 grid gap-8 md:grid-cols-3">
          {[
            ["Answer 10 questions", "Household size, income range, age, kids, and a few yes-or-no questions. No names, no documents."],
            ["See what fits", "Programs are sorted from strongest match to worth checking, with the reason for each."],
            ["Get your plan", "For every program: the documents to gather, where to apply, and how long it usually takes."],
          ].map(([title, text], i) => (
            <li key={title} className="flex gap-4">
              <span className="font-display flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent text-xl font-semibold text-brand-950">
                {i + 1}
              </span>
              <div>
                <h3 className="text-lg font-bold text-ink">{title}</h3>
                <p className="mt-1 text-muted">{text}</p>
              </div>
            </li>
          ))}
        </ol>
        <Link
          to="/quiz"
          className="mt-12 inline-flex min-h-12 items-center gap-2 font-semibold text-brand-700 underline decoration-2 underline-offset-4 hover:text-brand-900"
        >
          Start the questions
          <Icon name="arrowRight" className="h-4 w-4" />
        </Link>
      </section>
    </main>
  );
}

export default function App() {
  return (
    <Layout>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/quiz" element={<QuizWizard />} />
          <Route path="/results" element={<ResultsDashboard />} />
        </Routes>
      </ErrorBoundary>
    </Layout>
  );
}
