// Shared form for the sign in and sign up pages. Demo only: see config/demoAccount.js.
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import { DEMO_ACCOUNT, SHOW_DEMO_HINT } from "../../config/demoAccount.js";
import { safeNext } from "../../lib/userData.js";
import { Alert, Button, ErrorSummary, TextField } from "../ui/index.jsx";

export default function AuthForm({ mode }) {
  const isSignUp = mode === "signup";
  const { user, signIn, signUp, signOut } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [result, setResult] = useState(null);

  if (user) {
    return (
      <div className="space-y-4">
        <Alert variant="success" title={`You're signed in as ${user.email}`}>
          <p>You can go to your tracker or sign out to use a different account.</p>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Link to={safeNext(next, "/tracker")} className="btn btn-primary">Go to your tracker</Link>
          <Button variant="secondary" onClick={signOut}>Sign out</Button>
        </div>
      </div>
    );
  }

  const errors = result?.errors || {};
  // A form level error (wrong details) is shown on the first field so the summary can link to it.
  const summary = [
    ...Object.entries(errors).map(([id, message]) => ({ id: id === "confirm" ? "confirm" : id, message })),
    ...(result?.form ? [{ id: isSignUp ? "email" : "password", message: result.form }] : []),
  ];

  function onSubmit(e) {
    e.preventDefault();
    const r = isSignUp ? signUp(email, password, confirm) : signIn(email, password);
    if (r.ok) {
      const target = safeNext(next, r.applied ? "/matches" : "/tracker");
      navigate(target, { state: r.applied ? { flash: `${r.applied} was added to your tracker.` } : undefined });
    } else {
      setResult(r);
    }
  }

  const query = next ? `?next=${encodeURIComponent(next)}` : "";
  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      <Alert variant="info" title="Demo mode">
        <p>
          {isSignUp
            ? "Sign up only works with the Civis demo test account details. Any other details are rejected."
            : "Only the Civis test account is turned on."}
          {SHOW_DEMO_HINT && ` The demo email is ${DEMO_ACCOUNT.email}.`}
        </p>
      </Alert>
      <ErrorSummary items={summary} />
      <TextField
        id="email"
        label="Email address"
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={errors.email || (isSignUp ? result?.form : undefined)}
      />
      <div>
        <TextField
          id="password"
          label={isSignUp ? "Create a password" : "Password"}
          type={show ? "text" : "password"}
          autoComplete={isSignUp ? "new-password" : "current-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password || (!isSignUp ? result?.form : undefined)}
        />
        <label className="mt-2 flex min-h-11 items-center gap-2">
          <input type="checkbox" className="h-5 w-5" checked={show} onChange={(e) => setShow(e.target.checked)} />
          Show password
        </label>
      </div>
      {isSignUp && (
        <TextField
          id="confirm"
          label="Confirm password"
          type={show ? "text" : "password"}
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={errors.confirm}
        />
      )}
      <Button type="submit">{isSignUp ? "Create account" : "Sign in"}</Button>
      <p>
        {isSignUp ? (
          <>Already have an account? <Link to={`/signin${query}`}>Sign in</Link></>
        ) : (
          <>Don't have an account? <Link to={`/signup${query}`}>Sign up</Link></>
        )}
      </p>
    </form>
  );
}
