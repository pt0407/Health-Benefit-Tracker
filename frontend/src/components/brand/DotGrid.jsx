// A faint dot grid used as a quiet texture on navy surfaces (home hero, footer).
// Decorative only: low opacity, no motion, hidden from assistive tech.
import { useId } from "react";

export default function DotGrid({ className = "", color = "#ffffff", opacity = 0.09, gap = 22, radius = 1.4 }) {
  const id = `dots-${useId().replace(/:/g, "")}`;
  return (
    <svg aria-hidden="true" focusable="false" width="100%" height="100%" className={className}>
      <defs>
        <pattern id={id} patternUnits="userSpaceOnUse" width={gap} height={gap}>
          <circle cx={gap / 2} cy={gap / 2} r={radius} fill={color} fillOpacity={opacity} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
