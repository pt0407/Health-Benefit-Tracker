import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext.jsx";
import { CivisLogo } from "../brand/CivisLogo.jsx";
import Icon from "../shared/Icon.jsx";

const NAV = [
  { to: "/quiz", label: "Check benefits" },
  { to: "/matches", label: "Your matches" },
  { to: "/ask", label: "Ask Civis" },
  { to: "/tracker", label: "Tracker" },
];

// Closes a disclosure on Escape (returning focus to its button) and on a click outside.
function useDisclosure() {
  const [open, setOpen] = useState(false);
  const root = useRef(null);
  const button = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    const onClick = (e) => {
      if (root.current && !root.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);
  return { open, setOpen, root, button };
}

function AccountMenu() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const d = useDisclosure();
  return (
    <div ref={d.root} className="relative">
      <button
        ref={d.button}
        type="button"
        aria-expanded={d.open}
        aria-controls="account-menu"
        onClick={() => d.setOpen((o) => !o)}
        aria-label={`Account menu for ${user.email}`}
        className="flex min-h-11 items-center gap-1.5 border-2 border-white px-3 font-semibold text-white sm:max-w-xs"
      >
        <span className="truncate max-sm:hidden">{user.email}</span>
        <span className="sm:hidden">Account</span>
        <Icon name="chevronDown" className="h-4 w-4" />
      </button>
      {d.open && (
        <ul id="account-menu" className="absolute right-0 z-40 mt-1 w-56 border-2 border-ink bg-white py-1 text-ink">
          <li>
            <Link to="/tracker" onClick={() => d.setOpen(false)} className="block px-4 py-3 text-ink hover:bg-primary-lighter">Your tracker</Link>
          </li>
          <li>
            <Link to="/quiz" onClick={() => d.setOpen(false)} className="block px-4 py-3 text-ink hover:bg-primary-lighter">Edit your answers</Link>
          </li>
          <li>
            <button
              type="button"
              onClick={() => {
                d.setOpen(false);
                signOut();
                navigate("/");
              }}
              className="block w-full px-4 py-3 text-left font-semibold text-ink hover:bg-primary-lighter"
            >
              Sign out
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}

export default function Header() {
  const { user } = useAuth();
  const menu = useDisclosure();
  const { pathname } = useLocation();
  useEffect(() => menu.setOpen(false), [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const link = "block border-b-4 border-transparent py-3 font-semibold text-white no-underline hover:text-white hover:border-white/60 aria-[current=page]:border-accent md:mr-6";

  return (
    <header className="bg-primary-dark text-white print:hidden">
      <div className="container-page flex items-center justify-between gap-3 py-3">
        <Link to="/" aria-label="Civis home" className="text-white no-underline hover:text-white">
          <CivisLogo />
        </Link>
        <div ref={menu.root} className="flex items-center gap-2 sm:gap-3">
          {user ? (
            <AccountMenu />
          ) : (
            <>
              <Link to="/signin" className="px-2 py-2 font-semibold text-white hover:text-white">Sign in</Link>
              <Link
                to="/signup"
                className="border-2 border-white px-3 py-2 font-semibold text-white no-underline hover:bg-white hover:text-primary-dark"
              >
                Sign up
              </Link>
            </>
          )}
          <button
            ref={menu.button}
            type="button"
            aria-expanded={menu.open}
            aria-controls="main-nav"
            onClick={() => menu.setOpen((o) => !o)}
            className="flex min-h-11 items-center gap-1.5 px-2 font-semibold text-white md:hidden"
          >
            <Icon name="menu" className="h-5 w-5" />
            Menu
          </button>
        </div>
      </div>
      <nav aria-label="Main" id="main-nav" className={`${menu.open ? "block" : "hidden"} border-t border-white/25 md:block`}>
        <ul className="container-page md:flex">
          {NAV.map((n) => (
            <li key={n.to}>
              <NavLink to={n.to} className={link}>{n.label}</NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
