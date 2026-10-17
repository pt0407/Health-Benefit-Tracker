import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="mx-auto max-w-xl px-4 pt-16 pb-20 sm:px-6">
          <h1 className="text-3xl font-bold text-brand-900">Something went wrong on this page.</h1>
          <p className="mt-3 text-lg text-muted">Reloading usually fixes it. Your answers weren't saved, so you may need to start the questions again.</p>
          <button
            type="button"
            className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-brand-700 px-6 text-lg font-semibold text-white transition-colors hover:bg-brand-800"
            onClick={() => location.reload()}
          >
            Reload the page
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
