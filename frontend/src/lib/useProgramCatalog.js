import { useEffect, useState } from "react";
import { listPrograms } from "../api/benefitsApi.js";

let cache = null; // { byId } once loaded

export function useProgramCatalog() {
  const [state, setState] = useState(cache ? { status: "ready", byId: cache.byId } : { status: "loading", byId: {} });

  useEffect(() => {
    if (cache) return undefined;
    let cancelled = false;
    listPrograms()
      .then((programs) => {
        cache = { byId: Object.fromEntries(programs.map((p) => [p.program_id, p])) };
        if (!cancelled) setState({ status: "ready", byId: cache.byId });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error", byId: {} });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
