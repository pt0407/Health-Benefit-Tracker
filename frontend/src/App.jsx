import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/AuthContext.jsx";
import Layout from "./components/layout/Layout.jsx";
import QuizWizard from "./components/Quiz/QuizWizard.jsx";
import ErrorBoundary from "./components/shared/ErrorBoundary.jsx";
import Home from "./pages/Home.jsx";
import Matches from "./pages/Matches.jsx";
import NotFound from "./pages/NotFound.jsx";
import SignIn from "./pages/SignIn.jsx";
import SignUp from "./pages/SignUp.jsx";
import Tracker from "./pages/Tracker.jsx";

export default function App() {
  return (
    <Layout>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/quiz" element={<QuizWizard />} />
          <Route path="/matches" element={<Matches />} />
          <Route path="/results" element={<Navigate to="/matches" replace />} />
          <Route path="/tracker" element={<RequireAuth><Tracker /></RequireAuth>} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ErrorBoundary>
    </Layout>
  );
}
