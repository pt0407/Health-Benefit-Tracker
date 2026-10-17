import AuthForm from "../components/auth/AuthForm.jsx";
import { usePageTitle } from "../lib/usePageTitle.js";

export default function SignIn() {
  usePageTitle("Sign in");
  return (
    <div className="container-page max-w-xl py-10">
      <h1>Sign in</h1>
      <p className="mt-3 mb-6 text-lg">
        Sign in to track the programs you applied for. You don't need an account to take the quiz
        or see your matches.
      </p>
      <AuthForm mode="signin" />
    </div>
  );
}
