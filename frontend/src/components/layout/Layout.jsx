import Header from "./Header.jsx";
import Footer from "./Footer.jsx";

export default function Layout({ children }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:px-4 focus:py-3 focus:font-bold"
      >
        Skip to main content
      </a>
      <div className="border-b border-divider bg-surface-alt text-sm print:hidden">
        <p className="container-page py-1.5 text-ink">
          Civis is an independent student project. It is not a government website.
        </p>
      </div>
      <Header />
      <main id="main-content" tabIndex={-1} className="flex-1 outline-none">{children}</main>
      <Footer />
    </div>
  );
}
