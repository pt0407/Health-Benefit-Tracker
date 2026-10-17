import AuthForm from "../components/auth/AuthForm.jsx";
import { usePageTitle } from "../lib/usePageTitle.js";

export default function SignUp() {
  usePageTitle("Create an account");
  return (
    <div className="container-page max-w-xl py-10">
      <h1>Create an account</h1>
      <p className="mt-3 mb-6 text-lg">
        An account lets you save the programs you applied for and update their status. You don't
        need one to take the quiz or see your matches.
      </p>
      <AuthForm mode="signup" />
    </div>
  );
}
