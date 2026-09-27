import { Link, Route, Routes } from "react-router-dom";
import QuizWizard from "./components/Quiz/QuizWizard.jsx";
import ResultsDashboard from "./components/Results/ResultsDashboard.jsx";
import ErrorBoundary from "./components/shared/ErrorBoundary.jsx";

function Home() {
  return (
    <main className="mx-auto max-w-xl px-4 py-16 text-center">
      <h1 className="text-4xl font-bold">BenefitsFinder</h1>
      <p className="mt-3 text-lg text-gray-600">Find the benefits you're owed. In minutes.</p>
      <Link
        to="/quiz"
        className="mt-8 inline-block rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
      >
        Start
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/quiz" element={<QuizWizard />} />
        <Route path="/results" element={<ResultsDashboard />} />
      </Routes>
    </ErrorBoundary>
  );
}
