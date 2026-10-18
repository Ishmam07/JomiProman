import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import { Chip, ErrorBox, FindingList, Spinner } from "../components/common.jsx";
import { fmtArea, fmtDate, num } from "../utils.js";

export default function Flagged() {
  const { t } = useApp();
  const [deeds, setDeeds] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");

  const load = useCallback(() => {
    setError(null);
    setDeeds(null);
    api.flagged().then(setDeeds).catch(setError);
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (deeds || []).filter((d) => {
      if (filter === "blocked" && d.status !== "BLOCKED") return false;
      if (filter === "warn" && d.status === "BLOCKED") return false;
      if (!needle) return true;
      return [d.deed_no, d.mouza, d.seller, d.buyer, String(d.dag)].some((v) => String(v).toLowerCase().includes(needle));
    });
  }, [deeds, filter, q]);

  const FILTERS = [
    ["all", "flag.all"],
    ["blocked", "flag.onlyBlocked"],
    ["warn", "flag.onlyWarn"],
  ];

  return (
    <>
      <h1 className="page-title">{t("flag.title")}</h1>
      <p className="muted">{t("flag.sub")}</p>
      <ErrorBox error={error} />
      {!deeds && !error && <Spinner />}

      {deeds && deeds.length > 0 && (
        <div className="card toolbar">
          <div className="tabs inline-tabs" role="tablist">
            {FILTERS.map(([id, key]) => (
              <button key={id} type="button" role="tab" aria-selected={filter === id} className={filter === id ? "on" : ""} onClick={() => setFilter(id)}>
                {t(key)}
              </button>
            ))}
          </div>
          <input className="grow" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("flag.search")} aria-label={t("flag.search")} />
          <button type="button" className="btn btn-ghost" onClick={load}>
            ⟳ {t("flag.refresh")}
          </button>
          <span className="muted small">{t("flag.count", { n: num(shown.length) })}</span>
        </div>
      )}

      {deeds && deeds.length === 0 && (
        <div className="card">
          <p>
            {t("flag.empty")} <Link to="/register">{t("flag.emptyLink")}</Link>
          </p>
        </div>
      )}
      {deeds && deeds.length > 0 && shown.length === 0 && (
        <div className="card">
          <p className="muted">{t("flag.noMatch")}</p>
        </div>
      )}
      {shown.map((d) => (
        <article key={d.deed_no} className="card flagged">
          <div className="card-head">
            <h3>
              {d.deed_no} · {d.mouza}/{num(d.dag)}
            </h3>
            {d.status === "BLOCKED" ? <Chip status="RED">{t("plot.blocked")}</Chip> : <Chip status="AMBER">{t("flag.warnReg")}</Chip>}
          </div>
          <p>
            {d.seller} → {d.buyer} · {fmtArea(d.area)} {t("shatangsha")} · {fmtDate(d.deed_date)}
          </p>
          <FindingList findings={d.findings} />
          <div className="row">
            <Link className="btn btn-ghost" to={`/plot?mouza=${encodeURIComponent(d.mouza)}&dag=${d.dag}`}>
              {t("flag.viewPlot")}
            </Link>
            {d.status !== "BLOCKED" && (
              <Link className="btn btn-ghost" to={`/verify?deed=${d.deed_no}&hash=${d.fingerprint}`}>
                {t("reg.openVerify")}
              </Link>
            )}
          </div>
        </article>
      ))}
    </>
  );
}
