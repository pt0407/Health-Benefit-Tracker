// A flat row of arches, the shape from the Civis mark repeated like a colonnade.
// Decorative only: one flat color. Used on the home hero and above the footer.
import { useId } from "react";

export default function Arcade({ className = "", fill, height = 56, tile = 64 }) {
  const id = `arcade-${useId().replace(/:/g, "")}`;
  const gap = 16;
  const w = tile - gap;
  return (
    <svg aria-hidden="true" focusable="false" width="100%" height={height} className={className}>
      <defs>
        <pattern id={id} patternUnits="userSpaceOnUse" width={tile} height={height}>
          <path
            d={`M${gap / 2} ${height}V${w / 2}a${w / 2} ${w / 2} 0 0 1 ${w} 0V${height}Z`}
            fill={fill}
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
