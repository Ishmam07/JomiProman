import { useApp } from "../i18n.jsx";
import { STATUS, statusLabel } from "../utils.js";

export function Spinner({ label }) {
  const { t } = useApp();
  return (
    <div className="spinner" role="status">
      <span className="dot" />
      {label || t("wait")}
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="alert alert-red" role="alert">
      {error.message || String(error)}
    </div>
  );
}

export function StatusBanner({ status, title, children }) {
  useApp();
  const meta = STATUS[status] || STATUS.AMBER;
  return (
    <section className={`banner banner-${meta.cls}`} role="status">
      <div className="banner-icon" aria-hidden="true">
        {meta.icon}
      </div>
      <div>
        <div className="banner-tag">{statusLabel(status in STATUS ? status : "AMBER")}</div>
        <h2>{title}</h2>
        {children && <p>{children}</p>}
      </div>
    </section>
  );
}

export function Chip({ status, children }) {
  useApp();
  const meta = STATUS[status] || STATUS.AMBER;
  return <span className={`chip chip-${meta.cls}`}>{children ?? statusLabel(status in STATUS ? status : "AMBER")}</span>;
}

export function FindingList({ findings }) {
  if (!findings?.length) return null;
  return (
    <ul className="findings">
      {findings.map((f, i) => (
        <li key={`${f.code}-${i}`} className={`finding finding-${STATUS[f.severity]?.cls}`}>
          <span className="finding-dot" aria-hidden="true">
            {STATUS[f.severity]?.icon}
          </span>
          <span>{f.message}</span>
        </li>
      ))}
    </ul>
  );
}

export function ChecksList({ checks }) {
  if (!checks?.length) return null;
  return (
    <ul className="checks">
      {checks.map((c) => (
        <li key={c.key} className={c.ok === true ? "ok" : c.ok === false ? "bad" : "na"}>
          <span aria-hidden="true">{c.ok === true ? "✓" : c.ok === false ? "✕" : "–"}</span> {c.label}
        </li>
      ))}
    </ul>
  );
}
