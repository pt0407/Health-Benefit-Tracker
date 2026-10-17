import { Link, Route, Routes } from "react-router-dom";
import QuizWizard from "./components/Quiz/QuizWizard.jsx";
import ResultsDashboard from "./components/Results/ResultsDashboard.jsx";
import ErrorBoundary from "./components/shared/ErrorBoundary.jsx";
import Icon from "./components/shared/Icon.jsx";

function Layout({ children }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:font-semibold focus:text-brand-800"
      >
        Skip to content
      </a>
      <header className="on-brand bg-brand-900 text-white print:hidden">
        <div className="mx-auto flex h-14 max-w-3xl items-center px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <Icon name="shield" className="h-5 w-5 text-on-brand-muted" />
            BenefitsFinder
          </Link>
        </div>
      </header>
      <div id="main" className="flex-1">{children}</div>
      <footer className="border-t border-line print:hidden">
        <p className="mx-auto max-w-3xl px-4 py-6 text-sm text-subtle sm:px-6">
          BenefitsFinder is not a government website. Results are estimates
          from your answers; only the agency that runs a program can decide if you qualify.
        </p>
      </footer>
    </div>
  );
}

function Home() {
  return (
    <main className="mx-auto max-w-3xl px-4 pt-14 pb-20 sm:px-6 sm:pt-24">
      <h1 className="max-w-[16ch] text-4xl font-bold text-brand-900 sm:text-6xl">
        Find the benefits you're owed. In minutes.
      </h1>
      <p className="mt-5 max-w-[60ch] text-lg text-muted sm:text-xl">
        Answer 10 short questions about your household. We check federal programs and Texas
        state programs, then show you what you may qualify for and exactly how to apply.
      </p>
      <Link
        to="/quiz"
        className="mt-9 inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-700 px-6 text-lg font-semibold text-white transition-colors hover:bg-brand-800"
      >
        Check what I qualify for
        <Icon name="arrowRight" />
      </Link>
      <ul className="mt-12 grid gap-x-8 gap-y-3 text-muted sm:grid-cols-3">
        {[
          ["clock", "About 3 minutes"],
          ["list", "Food, health care, cash, and utility help"],
          ["shield", "No sign-up. Your answers aren't saved."],
        ].map(([icon, text]) => (
          <li key={text} className="flex items-start gap-2.5">
            <Icon name={icon} className="mt-0.5 h-5 w-5 text-brand-700" />
            <span>{text}</span>
          </li>
        ))}
      </ul>
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
