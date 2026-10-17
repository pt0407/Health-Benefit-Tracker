import { Link } from "react-router-dom";
import { usePageTitle } from "../lib/usePageTitle.js";

export default function NotFound() {
  usePageTitle("Page not found");
  return (
    <div className="container-page max-w-2xl py-16">
      <h1>Page not found</h1>
      <p className="mt-3 text-lg">The page you were looking for does not exist or has moved.</p>
      <p className="mt-6">
        <Link to="/" className="font-semibold">Go to the Civis home page</Link>
      </p>
    </div>
  );
}
