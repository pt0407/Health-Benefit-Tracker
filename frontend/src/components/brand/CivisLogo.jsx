// Civis mark: an open arch, like a civic doorway, drawn as the letter C, with one
// small figure standing inside it. Civis is Latin for citizen. Single color
// (currentColor) so it works on any background. Minimum size 16px.

export function CivisMark({ className = "h-8 w-8", title }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      className={`shrink-0 ${className}`}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      <path d="M37.02 13.07A17 17 0 1 0 37.02 34.93" stroke="currentColor" strokeWidth="5.5" />
      <circle cx="24" cy="20.5" r="3.8" fill="currentColor" />
      <path d="M16.5 33a7.5 7.5 0 0 1 15 0Z" fill="currentColor" />
    </svg>
  );
}

export function CivisLogo({ className = "", markClassName = "h-9 w-9" }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <CivisMark className={markClassName} />
      <span className="text-[1.5rem] leading-none font-bold tracking-tight">Civis</span>
    </span>
  );
}
