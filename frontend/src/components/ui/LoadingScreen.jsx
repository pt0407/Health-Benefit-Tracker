// Full-screen loading view with a spinning circle. Shown from the moment the quiz is
// submitted until the matches are on screen. role="status" announces it politely.
export default function LoadingScreen({ title = "Checking programs for your household", note = "This can take up to a minute the first time." }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-white px-6 text-center"
    >
      <span
        aria-hidden="true"
        className="civis-spinner block h-16 w-16 rounded-full border-[6px] border-primary-light border-t-primary"
      />
      <div>
        <p className="text-2xl font-bold text-primary-dark">{title}</p>
        <p className="mt-2 text-muted">{note}</p>
      </div>
    </div>
  );
}
