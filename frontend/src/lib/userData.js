// Everything Civis keeps in this browser: saved quiz answers, the latest results,
// the application tracker, and a one-shot "I applied" intent that survives sign in.
// Pure functions over storage.js, so they can be tested without a browser.
import { readEntry, readJSON, writeJSON, removeKey } from "./storage.js";
import { normalizeEmail } from "./credentials.js";

export const STATUSES = ["Not started", "Preparing", "Submitted", "Under review", "Approved", "Denied"];
const PENDING_MAX_AGE_MS = 30 * 60 * 1000;

export const scopeFor = (email) => (email ? normalizeEmail(email) : "guest");

export function todayISO(now = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// Only same-site paths are allowed as a redirect target after sign in.
export function safeNext(next, fallback) {
  if (typeof next !== "string" || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return fallback;
  return next;
}

// ---- Quiz answers and results ----

export function getAnswers(scope) {
  const e = readEntry(`answers:${scope}`);
  return e ? { answers: e.data.answers, complete: !!e.data.complete, savedAt: e.savedAt } : null;
}
export function saveAnswers(scope, answers, { complete = false } = {}) {
  return writeJSON(`answers:${scope}`, { answers, complete });
}
export function clearAnswers(scope) {
  removeKey(`answers:${scope}`);
}
export function getResults(scope) {
  const e = readEntry(`results:${scope}`);
  return e ? { result: e.data, savedAt: e.savedAt } : null;
}
export function saveResults(scope, result) {
  return writeJSON(`results:${scope}`, result);
}

// ---- Tracker ----

const trackerKey = (email) => `tracker:${normalizeEmail(email)}`;
const slug = (s) => String(s ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function entryKeyFor(program) {
  return program.program_id || slug(program.program);
}

export function getTracker(email) {
  const data = readJSON(trackerKey(email), []);
  return Array.isArray(data) ? data : [];
}
export function saveTracker(email, entries) {
  return writeJSON(trackerKey(email), entries);
}

function documentsFor(program) {
  const raw = program.documents?.length
    ? program.documents
    : (program.next_steps || []).flatMap((s) => s.documents || []);
  return [...new Set(raw)].map((label) => ({ label, done: false }));
}

// Adds one entry per program. Applying twice never duplicates.
export function addTrackerEntry(email, program, now = new Date()) {
  const entries = getTracker(email);
  const id = entryKeyFor(program);
  const existing = entries.find((e) => e.id === id);
  if (existing) return { entries, entry: existing, added: false };
  const entry = {
    id,
    name: program.program,
    category: program.category ?? "other",
    level: program.level ?? "unknown",
    monthlyValue: program.monthly_value_usd ?? 0,
    applicationUrl: program.application_url ?? null,
    status: "Submitted",
    dateApplied: todayISO(now),
    confirmationNumber: "",
    notes: "",
    documents: documentsFor(program),
    addedAt: now.toISOString(),
    updatedAt: now.toISOString(),
  };
  const next = [...entries, entry];
  saveTracker(email, next);
  return { entries: next, entry, added: true };
}

export function updateTrackerEntry(email, id, patch, now = new Date()) {
  const next = getTracker(email).map((e) => (e.id === id ? { ...e, ...patch, updatedAt: now.toISOString() } : e));
  saveTracker(email, next);
  return next;
}

export function removeTrackerEntry(email, id) {
  const next = getTracker(email).filter((e) => e.id !== id);
  saveTracker(email, next);
  return next;
}

// ---- "I applied" intent kept across the sign in round trip ----

export function setPendingApply(snapshot, now = Date.now()) {
  return writeJSON("pending-apply", { snapshot, at: now });
}
export function takePendingApply(now = Date.now()) {
  const data = readJSON("pending-apply", null);
  removeKey("pending-apply");
  if (!data || typeof data.at !== "number" || now - data.at > PENDING_MAX_AGE_MS) return null;
  return data.snapshot ?? null;
}

// ---- Guest data carried into an account ----

// Newer guest answers and results replace the account's copy; the guest copy is then cleared.
export function mergeGuestInto(email) {
  const scope = scopeFor(email);
  for (const kind of ["answers", "results"]) {
    const guest = readEntry(`${kind}:guest`);
    if (!guest) continue;
    const mine = readEntry(`${kind}:${scope}`);
    if (!mine || guest.savedAt > mine.savedAt) writeJSON(`${kind}:${scope}`, guest.data);
    removeKey(`${kind}:guest`);
  }
}
