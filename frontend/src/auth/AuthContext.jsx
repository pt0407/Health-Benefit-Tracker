// Demo-only session handling. See config/demoAccount.js: this is not real security.
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { checkSignIn, checkSignUp } from "../lib/credentials.js";
import { readJSON, removeKey, writeJSON } from "../lib/storage.js";
import { addTrackerEntry, mergeGuestInto, takePendingApply } from "../lib/userData.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const s = readJSON("session", null);
    return s?.email ? { email: s.email } : null;
  });

  const start = useCallback((email) => {
    writeJSON("session", { email, signedInAt: new Date().toISOString() });
    mergeGuestInto(email);
    // An "I applied" pressed before signing in is finished now.
    const pending = takePendingApply();
    const added = pending ? addTrackerEntry(email, pending) : null;
    setUser({ email });
    return { ok: true, applied: added?.added ? pending.program : null };
  }, []);

  const signIn = useCallback(
    (email, password) => {
      const r = checkSignIn(email, password);
      return r.ok ? start(r.email) : r;
    },
    [start],
  );

  const signUp = useCallback(
    (email, password, confirm) => {
      const r = checkSignUp(email, password, confirm);
      return r.ok ? start(r.email) : r;
    },
    [start],
  );

  const signOut = useCallback(() => {
    removeKey("session");
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, signIn, signUp, signOut }), [user, signIn, signUp, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function RequireAuth({ children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (!user) {
    return <Navigate to={`/signin?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  }
  return children;
}
