// Display labels and filter helpers for the program catalog (GET /api/programs).
// The match response has no category, level or numeric processing days, so those
// come from the catalog, joined on program_id.

export const CATEGORY_LABELS = {
  nutrition: "Food",
  health: "Health coverage",
  energy: "Utilities",
  disability: "Disability",
  cash: "Cash help",
  employment: "Work and unemployment",
  education: "Education and child care",
  legal: "Legal help",
  other: "Other",
};

// Icon names from components/shared/Icon.jsx.
export const CATEGORY_ICONS = {
  nutrition: "basket",
  health: "heart",
  energy: "bolt",
  disability: "shield",
  cash: "wallet",
  employment: "briefcase",
  education: "book",
  legal: "scale",
  other: "list",
};

export const LEVEL_LABELS = {
  federal: "Federal",
  state: "Texas",
  federal_state: "Federal and Texas",
  unknown: "Not listed",
};

export const BUCKETS = [
  { value: "30", label: "30 days or less" },
  { value: "90", label: "31 to 90 days" },
  { value: "over", label: "More than 90 days" },
  { value: "unknown", label: "Not stated" },
];

export function levelMatches(type, filter) {
  if (!filter || filter === "all") return true;
  if (filter === "federal") return type === "federal" || type === "federal_state";
  if (filter === "texas") return type === "state" || type === "federal_state";
  return true;
}

// Null never means zero: a program with no stated time lands in "unknown".
export function processingBucket(days) {
  if (days == null || Number.isNaN(days)) return "unknown";
  if (days <= 30) return "30";
  if (days <= 90) return "90";
  return "over";
}

export function parseDays(text) {
  const m = /(\d+)\s*days?/i.exec(String(text ?? ""));
  return m ? Number(m[1]) : null;
}

// Join one match with its catalog record, with fallbacks when there is none.
export function enrich(match, byId) {
  const rec = match.program_id ? byId?.[match.program_id] : null;
  const days = rec ? rec.processing_time_days ?? null : parseDays(match.processing_time);
  const documents = rec?.documents_needed?.length
    ? rec.documents_needed
    : (match.next_steps || []).flatMap((s) => s.documents || []);
  return {
    ...match,
    category: rec?.category ?? "other",
    level: rec?.type ?? "unknown",
    processingDays: days,
    bucket: processingBucket(days),
    documents,
  };
}
