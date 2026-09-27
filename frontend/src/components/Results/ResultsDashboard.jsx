// Owner: Person 3. See docs/BUILD_PLAN.md §3 Component 7.
// Receives the MatchResponse (backend/models/match_result.py) via router state.

import { useLocation } from "react-router-dom";

export default function ResultsDashboard() {
  const result = useLocation().state;

  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h2 className="text-2xl font-bold">Results</h2>
      {result ? (
        <p className="mt-2">
          You may qualify for ${result.total_estimated_annual_value.toLocaleString()}/year across{" "}
          {result.program_count} programs.
        </p>
      ) : (
        <p className="mt-2 text-gray-600">Take the quiz to see your results.</p>
      )}
    </main>
  );
}
