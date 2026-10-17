import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="container-page max-w-2xl py-16">
          <h1>Something went wrong on this page</h1>
          <p className="mt-3 text-lg">
            Reloading usually fixes it. Your answers are saved in this browser, so reloading should
            bring them back.
          </p>
          <button type="button" className="btn btn-primary mt-8" onClick={() => location.reload()}>
            Reload the page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
