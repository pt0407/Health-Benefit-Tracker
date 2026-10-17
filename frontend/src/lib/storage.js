// Guarded localStorage access. Storage can be blocked (private windows, strict
// settings) or hold invalid JSON, so every call falls back instead of throwing.
// Values are saved as { v: 1, savedAt, data } under keys prefixed "civis:".

const PREFIX = "civis:";

function store() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function readEntry(key) {
  try {
    const s = store();
    if (!s) return null;
    const raw = s.getItem(PREFIX + key);
    if (raw == null) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && parsed.v === 1) return parsed;
    return null;
  } catch {
    return null;
  }
}

export function readJSON(key, fallback = null) {
  const entry = readEntry(key);
  return entry ? entry.data : fallback;
}

export function writeJSON(key, data) {
  try {
    const s = store();
    if (!s) return false;
    s.setItem(PREFIX + key, JSON.stringify({ v: 1, savedAt: new Date().toISOString(), data }));
    return true;
  } catch {
    return false;
  }
}

export function removeKey(key) {
  try {
    store()?.removeItem(PREFIX + key);
  } catch {
    // Nothing to do: storage is unavailable.
  }
}
