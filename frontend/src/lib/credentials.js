// Pure sign in and sign up checks for the demo account. No React, no storage.
import { DEMO_ACCOUNT } from "../config/demoAccount.js";

export const normalizeEmail = (email) => String(email ?? "").trim().toLowerCase();

const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const matchesDemo = (email, password) =>
  normalizeEmail(email) === normalizeEmail(DEMO_ACCOUNT.email) && password === DEMO_ACCOUNT.password;

export function checkSignIn(email, password) {
  const errors = {};
  if (!normalizeEmail(email)) errors.email = "Enter your email address.";
  else if (!EMAIL_SHAPE.test(normalizeEmail(email))) errors.email = "Enter an email address in the format name@example.com.";
  if (!password) errors.password = "Enter your password.";
  if (Object.keys(errors).length) return { ok: false, errors };
  if (!matchesDemo(email, password)) {
    return { ok: false, errors: {}, form: "That email and password don't match our records. Check them and try again." };
  }
  return { ok: true, email: normalizeEmail(email) };
}

export function checkSignUp(email, password, confirm) {
  const errors = {};
  if (!normalizeEmail(email)) errors.email = "Enter your email address.";
  else if (!EMAIL_SHAPE.test(normalizeEmail(email))) errors.email = "Enter an email address in the format name@example.com.";
  if (!password) errors.password = "Create a password.";
  if (!confirm) errors.confirm = "Enter your password again.";
  else if (password && confirm !== password) errors.confirm = "The two passwords don't match.";
  if (Object.keys(errors).length) return { ok: false, errors };
  if (!matchesDemo(email, password)) {
    return {
      ok: false,
      errors: {},
      form: "Civis is running in demo mode. New accounts can't be created yet. Only the demo test account is turned on.",
    };
  }
  return { ok: true, email: normalizeEmail(email) };
}
