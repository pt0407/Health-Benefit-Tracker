// Small shared pieces in the style of public service forms: flat, plain, labelled.
import { forwardRef, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import Icon from "../shared/Icon.jsx";

export function Button({ variant = "primary", className = "", type = "button", ...props }) {
  return <button type={type} className={`btn btn-${variant} ${className}`} {...props} />;
}

export function LinkButton({ variant = "primary", className = "", ...props }) {
  return <Link className={`btn btn-${variant} ${className}`} {...props} />;
}

const ALERT_STYLES = {
  info: { box: "border-info bg-info-bg", icon: "info" },
  success: { box: "border-success bg-success-bg", icon: "check" },
  warning: { box: "border-warning bg-warning-bg", icon: "alert" },
  error: { box: "border-error bg-error-bg", icon: "alert" },
};

// Errors are announced immediately (role alert); the rest politely (role status).
export function Alert({ variant = "info", title, children, onDismiss, className = "" }) {
  const s = ALERT_STYLES[variant];
  return (
    <div
      role={variant === "error" ? "alert" : "status"}
      className={`flex gap-3 rounded-lg border-l-8 p-4 ${s.box} ${className}`}
    >
      <Icon name={s.icon} className="mt-0.5 h-5 w-5" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-bold">{title}</p>}
        <div className="[&>p+p]:mt-2">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss message"
          className="-m-2 flex h-11 w-11 items-center justify-center"
        >
          <Icon name="close" className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}

export function Tag({ children, tone = "neutral", className = "" }) {
  const tones = {
    neutral: "border-border bg-surface-alt text-ink",
    primary: "border-primary-dark bg-primary-light text-primary-dark",
    success: "border-success-text bg-success-bg text-success-text",
    error: "border-error bg-error-bg text-error",
    warning: "border-warning bg-warning-bg text-ink",
  };
  return (
    <span className={`inline-block border px-2 py-0.5 text-sm font-semibold ${tones[tone]} ${className}`}>
      {children}
    </span>
  );
}

// A label above the control, optional hint, and an error message wired with aria-describedby.
export function TextField({ id, label, hint, error, type = "text", className = "", inputClassName = "", ...props }) {
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`${error ? "border-l-4 border-error pl-4" : ""} ${className}`}>
      <label htmlFor={id} className="block font-semibold">{label}</label>
      {hint && <p id={`${id}-hint`} className="text-muted">{hint}</p>}
      {error && (
        <p id={`${id}-error`} className="font-semibold text-error">
          <span className="sr-only">Error: </span>
          {error}
        </p>
      )}
      <input
        id={id}
        type={type}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={describedBy}
        className={`input mt-1 ${inputClassName}`}
        {...props}
      />
    </div>
  );
}

// GOV.UK style: shown at the top after a failed submit, takes focus, links to each field.
export const ErrorSummary = forwardRef(function ErrorSummary({ items }, _ref) {
  const ref = useRef(null);
  useEffect(() => {
    if (items.length) ref.current?.focus();
  }, [items]);
  if (!items.length) return null;
  return (
    <div ref={ref} tabIndex={-1} role="alert" className="border-4 border-error p-4" aria-labelledby="error-summary-title">
      <h2 id="error-summary-title" className="text-xl">There is a problem</h2>
      <ul className="mt-2 list-disc pl-5">
        {items.map((it) => (
          <li key={it.id}>
            {it.id ? (
              <a href={`#${it.id}`} className="font-semibold text-error">{it.message}</a>
            ) : (
              <span className="font-semibold text-error">{it.message}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
});
