import { Link } from "react-router-dom";
import DotGrid from "../brand/DotGrid.jsx";
import { CivisLogo } from "../brand/CivisLogo.jsx";

const link = "text-white underline hover:text-white hover:decoration-2";

export default function Footer() {
  return (
    <footer className="mt-16 print:hidden">
      <div className="relative overflow-hidden bg-primary-dark text-white">
        <DotGrid className="pointer-events-none absolute inset-0" />
        <div className="container-page relative grid gap-8 py-12 md:grid-cols-[1.4fr_1fr]">
          <div className="space-y-3">
            <CivisLogo markClassName="h-8 w-8" />
            <p className="max-w-[60ch]">
              Estimates only: the agency that runs a program decides if you qualify. Your answers and
              tracker are saved in this browser and sent to Civis only to check programs.
            </p>
          </div>
          <nav aria-label="Footer">
            <h2 className="text-lg text-white">Pages</h2>
            <ul className="mt-2 space-y-1.5">
              <li><Link to="/quiz" className={link}>Check benefits</Link></li>
              <li><Link to="/matches" className={link}>Your matches</Link></li>
              <li><Link to="/tracker" className={link}>Tracker</Link></li>
              <li><Link to="/signin" className={link}>Sign in</Link></li>
            </ul>
          </nav>
        </div>
      </div>
    </footer>
  );
}
