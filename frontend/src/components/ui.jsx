// Shared enterprise primitives: Card, PageHeader, states, Alert.
import { Link } from "react-router-dom";

export function Card({ children, className = "", hover = false }) {
  return <div className={`card card-pad${hover ? " card-hover" : ""} ${className}`}>{children}</div>;
}

export function PageHeader({ title, description, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
      <div>
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-desc">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function SectionTitle({ children }) {
  return <h2 className="section-title mb-2">{children}</h2>;
}

export function LoadingState({ text = "Loading…" }) {
  return (
    <div className="card card-pad space-y-2" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <span className="spinner" aria-hidden="true" />
        {text}
      </div>
      <div className="skeleton" style={{ height: 12 }} />
      <div className="skeleton" style={{ height: 12, width: "70%" }} />
    </div>
  );
}

export function EmptyState({ text, action }) {
  return (
    <div className="card card-pad text-center py-8">
      <p className="text-sm text-slate-500">{text}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="alert alert-error" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-sm btn-secondary ml-3">
          Retry
        </button>
      )}
    </div>
  );
}

export function Alert({ kind = "info", children }) {
  return (
    <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function BackendUnreachable({ onRetry, detail }) {
  const message = detail
    ? `Backend is unreachable (${detail}). Start it with uvicorn app.main:app --reload in backend/.`
    : "Backend is unreachable. Start it with uvicorn app.main:app --reload in backend/.";
  return <ErrorState message={message} onRetry={onRetry} />;
}

export function UploadLink() {
  return (
    <Link to="/upload" className="btn btn-primary btn-sm">
      Upload configuration
    </Link>
  );
}
