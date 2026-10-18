import { Component } from "react";

/** Shows the error instead of a blank white page if any component crashes while rendering. */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("UI crash:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ maxWidth: 640, margin: "3rem auto", padding: "1rem", fontFamily: "sans-serif" }}>
        <h2>কিছু একটা সমস্যা হয়েছে / Something went wrong</h2>
        <pre style={{ whiteSpace: "pre-wrap", background: "#fee", color: "#600", padding: "0.75rem", borderRadius: 6, fontSize: 13 }}>
          {String(this.state.error?.message || this.state.error)}
          {"\n\n"}
          {String(this.state.error?.stack || "").split("\n").slice(0, 6).join("\n")}
        </pre>
        <button onClick={() => (window.location.href = "/")}>Reload / আবার চেষ্টা করুন</button>
      </div>
    );
  }
}
