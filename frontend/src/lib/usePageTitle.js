import { useEffect } from "react";

let firstPage = true;

// Sets the tab title and, on in-app navigation, moves focus to the page heading so
// screen readers announce the new page. The very first load is left alone.
export function usePageTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} | Civis` : "Civis: find the benefits you may qualify for";
    if (firstPage) {
      firstPage = false;
      return;
    }
    window.scrollTo(0, 0);
    const h1 = document.querySelector("main h1");
    if (h1) {
      h1.setAttribute("tabindex", "-1");
      h1.focus({ preventScroll: true });
    }
  }, [title]);
}
