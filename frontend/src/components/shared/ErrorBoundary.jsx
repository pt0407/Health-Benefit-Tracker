import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="mx-auto max-w-xl px-4 py-16 text-center">
          <h2 className="text-xl font-semibold">Something went wrong.</h2>
          <button className="mt-4 underline" onClick={() => location.reload()}>
            Reload
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
