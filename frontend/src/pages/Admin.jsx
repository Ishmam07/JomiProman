import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import { ErrorBox, Spinner } from "../components/common.jsx";
import { fmtArea, fmtDate, num } from "../utils.js";

const KEY_STORAGE = "jomiproman.adminKey";
const PAGE_SIZE = 50;
const emptyPage = { items: [], total: 0, page: 1, page_size: PAGE_SIZE };
const safeDate = (iso, lang) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(lang === "bn" ? "bn-BD" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
};

function Metric({ icon, label, value, tone = "" }) {
  return <article className={`admin-metric ${tone}`}><span className="admin-metric-icon" aria-hidden="true">{icon}</span><div><span>{label}</span><strong>{value == null ? "—" : num(value)}</strong></div></article>;
}
function ServiceTile({ icon, title, value, detail, ok = true }) {
  return <div className="admin-service"><span className="admin-service-icon">{icon}</span><div className="admin-service-copy"><strong>{title}</strong><span>{detail || value}</span></div><span className={`admin-pulse ${ok ? "is-ok" : "is-warn"}`} title={value} /> </div>;
}
function Outcome({ value }) {
  const v = String(value || "unknown").toLowerCase();
  return <span className={`admin-pill admin-pill-${v}`}>{value || "—"}</span>;
}

export default function Admin() {
  const { t, lang } = useApp();
  const [key, setKey] = useState(() => {
    try { return sessionStorage.getItem(KEY_STORAGE) || ""; } catch { return ""; }
  });
  const [authorized, setAuthorized] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [audit, setAudit] = useState(emptyPage);
  const [deeds, setDeeds] = useState(emptyPage);
  const [plots, setPlots] = useState(emptyPage);
  const [auditFilters, setAuditFilters] = useState({ q: "", action: "", outcome: "" });
  const [deedFilters, setDeedFilters] = useState({ q: "", status: "", risk: "", mutation: "" });
  const [plotQuery, setPlotQuery] = useState("");
  const [notice, setNotice] = useState("");

  const loadAudit = useCallback(async (token, page = 1, append = false, filters = auditFilters) => {
    const result = await api.adminAudit(token, { ...filters, page, page_size: PAGE_SIZE });
    setAudit((old) => ({ ...result, items: append ? [...old.items, ...result.items] : result.items }));
  }, [auditFilters]);
  const loadDeeds = useCallback(async (token, page = 1, append = false, filters = deedFilters) => {
    const result = await api.adminDeeds(token, { ...filters, page, page_size: PAGE_SIZE });
    setDeeds((old) => ({ ...result, items: append ? [...old.items, ...result.items] : result.items }));
  }, [deedFilters]);
  const loadPlots = useCallback(async (token, page = 1, append = false, q = plotQuery) => {
    const result = await api.adminPlots(token, { q, page, page_size: PAGE_SIZE });
    setPlots((old) => ({ ...result, items: append ? [...old.items, ...result.items] : result.items }));
  }, [plotQuery]);

  const connectWithKey = useCallback(async (token) => {
    if (!token.trim()) { setError(new Error(t("admin.keyRequired"))); return; }
    setConnecting(true); setError(null); setNotice("");
    try {
      const data = await api.adminOverview(token.trim());
      setOverview(data);
      setAuthorized(true);
      setKey(token.trim());
      try { sessionStorage.setItem(KEY_STORAGE, token.trim()); } catch { /* private mode */ }
      const results = await Promise.allSettled([
        api.adminAudit(token.trim(), { page: 1, page_size: PAGE_SIZE }),
        api.adminDeeds(token.trim(), { page: 1, page_size: PAGE_SIZE }),
        api.adminPlots(token.trim(), { page: 1, page_size: PAGE_SIZE }),
      ]);
      if (results[0].status === "fulfilled") setAudit(results[0].value);
      if (results[1].status === "fulfilled") setDeeds(results[1].value);
      if (results[2].status === "fulfilled") setPlots(results[2].value);
      setNotice(t("admin.connected"));
    } catch (err) {
      setAuthorized(false);
      setOverview(null);
      setError(err);
    } finally { setConnecting(false); }
  }, [t]);

  useEffect(() => {
    let initial = "";
    try { initial = sessionStorage.getItem(KEY_STORAGE) || ""; } catch { /* storage unavailable */ }
    if (initial) connectWithKey(initial);
  // connect only once for a key already saved in this tab
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshAll() {
    if (!key) return;
    setLoading(true); setError(null); setNotice("");
    try {
      const o = await api.adminOverview(key);
      setOverview(o);
      await Promise.all([loadAudit(key, 1, false), loadDeeds(key, 1, false), loadPlots(key, 1, false)]);
      setNotice(t("admin.refreshed"));
    } catch (err) { setError(err); if (err.status === 401) disconnect(); }
    finally { setLoading(false); }
  }
  function disconnect() {
    setAuthorized(false); setOverview(null); setKey(""); setError(null); setNotice("");
    try { sessionStorage.removeItem(KEY_STORAGE); } catch { /* storage unavailable */ }
  }
  async function downloadCsv() {
    setError(null);
    try {
      const blob = await api.adminAuditCsv(key);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "jomiproman-audit.csv"; a.click();
      URL.revokeObjectURL(url);
      setNotice(t("admin.exported"));
    } catch (err) { setError(err); }
  }
  async function searchAudit(e) { e.preventDefault(); setLoading(true); setError(null); try { await loadAudit(key, 1, false, auditFilters); } catch (err) { setError(err); } finally { setLoading(false); } }
  async function searchDeeds(e) { e.preventDefault(); setLoading(true); setError(null); try { await loadDeeds(key, 1, false, deedFilters); } catch (err) { setError(err); } finally { setLoading(false); } }
  async function searchPlots(e) { e.preventDefault(); setLoading(true); setError(null); try { await loadPlots(key, 1, false, plotQuery); } catch (err) { setError(err); } finally { setLoading(false); } }

  const tabs = [
    ["overview", t("admin.tabOverview"), "◫"], ["activity", t("admin.tabActivity"), "↻"],
    ["deeds", t("admin.tabDeeds"), "▤"], ["plots", t("admin.tabPlots"), "⌖"], ["system", t("admin.tabSystem"), "⚙"],
  ];
  const metrics = overview?.metrics;

  if (!authorized) return (
    <div className="admin-shell admin-gate">
      <section className="admin-gate-card">
        <div className="admin-gate-mark">⌘</div>
        <p className="eyebrow">{t("admin.eyebrow")}</p>
        <h1 className="page-title">{t("admin.title")}</h1>
        <p className="muted">{t("admin.loginSub")}</p>
        <form className="admin-login-form" onSubmit={(e) => { e.preventDefault(); connectWithKey(key); }}>
          <label htmlFor="admin-key">{t("admin.keyLabel")}</label>
          <input id="admin-key" type="password" autoComplete="current-password" value={key} onChange={(e) => setKey(e.target.value)} placeholder={t("admin.keyPlaceholder")} required />
          <button className="btn btn-primary btn-lg" type="submit" disabled={connecting}>{connecting ? t("admin.connecting") : t("admin.connect")}</button>
        </form>
        <ErrorBox error={error} />
        <p className="small muted">{t("admin.keyHint")}</p>
      </section>
      <aside className="admin-gate-aside">
        <span className="admin-gate-overline">{t("admin.secureSpace")}</span>
        <h2>{t("admin.gateTitle")}</h2>
        <p>{t("admin.gateBody")}</p>
        <div className="admin-gate-points"><span>✓ {t("admin.gatePoint1")}</span><span>✓ {t("admin.gatePoint2")}</span><span>✓ {t("admin.gatePoint3")}</span></div>
      </aside>
    </div>
  );

  return (
    <section className="admin-shell">
      <header className="admin-page-head">
        <div className="admin-title-group">
          <p className="eyebrow">{t("admin.eyebrow")}</p>
          <h1 className="page-title">{t("admin.title")}</h1>
          <p className="muted">{t("admin.subtitle")}</p>
        </div>
        <div className="admin-head-actions">
          <span className="admin-live"><span /> {t("admin.live")}</span>
          <button type="button" className="btn btn-ghost" onClick={refreshAll} disabled={loading}>{loading ? "⟳ …" : "⟳ " + t("admin.refresh")}</button>
          <button type="button" className="btn btn-ghost" onClick={downloadCsv}>⇩ {t("admin.exportCsv")}</button>
          <button type="button" className="btn btn-ghost" onClick={disconnect}>{t("admin.disconnect")}</button>
        </div>
      </header>
      <ErrorBox error={error} />
      {notice && <div className="admin-notice" role="status">✓ {notice}</div>}
      {loading && <Spinner label={t("admin.refreshing")} />}

      <nav className="admin-tabs" aria-label={t("admin.adminSections")}>
        {tabs.map(([id, label, icon]) => <button type="button" key={id} className={tab === id ? "active" : ""} aria-pressed={tab === id} onClick={() => setTab(id)}><span>{icon}</span>{label}</button>)}
      </nav>

      {tab === "overview" && overview && <>
        <div className="admin-metrics-grid">
          <Metric icon="⌖" label={t("admin.metricPlots")} value={metrics.plots} />
          <Metric icon="▤" label={t("admin.metricDeeds")} value={metrics.deeds_total} />
          <Metric icon="✓" label={t("admin.metricRegistered")} value={metrics.deeds_registered} tone="metric-green" />
          <Metric icon="!" label={t("admin.metricBlocked")} value={metrics.deeds_blocked} tone="metric-red" />
          <Metric icon="◷" label={t("admin.metricPending")} value={metrics.mutation_pending} tone="metric-amber" />
          <Metric icon="↻" label={t("admin.metricActivity")} value={metrics.activity_today} />
        </div>
        <div className="admin-two-col">
          <section className="card admin-panel-card">
            <div className="admin-section-head"><div><h2>{t("admin.riskTitle")}</h2><p>{t("admin.riskSub")}</p></div><span className="admin-mini-total">{num(metrics.deeds_total)}</span></div>
            <div className="risk-bars">
              {[ ["GREEN", t("status.GREEN"), "risk-green"], ["AMBER", t("status.AMBER"), "risk-amber"], ["RED", t("status.RED"), "risk-red"] ].map(([id, label, cls]) => {
                const n = overview.risk_breakdown?.[id] || 0;
                const pct = metrics.deeds_total ? Math.round(n / metrics.deeds_total * 100) : 0;
                return <div className="risk-bar-row" key={id}><div className="risk-bar-label"><span>{label}</span><strong>{num(n)} <small>{num(pct)}%</small></strong></div><div className="risk-bar-track"><span className={cls} style={{ width: `${pct}%` }} /></div></div>;
              })}
            </div>
            <div className="admin-stat-foot"><span>{t("admin.flaggedTotal")}</span><strong>{num(metrics.deeds_flagged)}</strong><span>{t("admin.mutationDone")}: <strong>{num(metrics.mutation_done)}</strong></span></div>
          </section>
          <section className="card admin-panel-card">
            <div className="admin-section-head"><div><h2>{t("admin.servicesTitle")}</h2><p>{t("admin.servicesSub")}</p></div><span className="admin-health-pill">{t("admin.online")}</span></div>
            <div className="admin-service-list">
              <ServiceTile icon="▦" title={t("admin.database")} value="up" detail={t("admin.connectedDb")} />
              <ServiceTile icon="ϟ" title="Redis" value={overview.services.cache} detail={overview.services.cache} ok={overview.services.cache !== "unavailable"} />
              <ServiceTile icon="✧" title="AI / Groq" value={overview.services.ai_enabled ? t("admin.configured") : t("admin.fallback")} detail={overview.services.ai_model || t("admin.noApiKey")} ok={overview.services.ai_enabled} />
              <ServiceTile icon="⌑" title={t("admin.signing")} value={overview.services.signing_algorithm} detail={`${t("admin.keyId")}: ${overview.services.signing_key_id}`} />
            </div>
          </section>
        </div>
        <section className="card admin-panel-card">
          <div className="admin-section-head"><div><h2>{t("admin.recentActivity")}</h2><p>{t("admin.recentActivitySub")}</p></div><button className="btn btn-ghost" onClick={() => setTab("activity")}>{t("admin.viewAll")} →</button></div>
          <AuditTable items={overview.recent_events || []} lang={lang} t={t} compact />
        </section>
        <section className="card admin-panel-card">
          <div className="admin-section-head"><div><h2>{t("admin.latestDeeds")}</h2><p>{t("admin.latestDeedsSub")}</p></div><button className="btn btn-ghost" onClick={() => setTab("deeds")}>{t("admin.viewAll")} →</button></div>
          <DeedTable items={overview.recent_deeds || []} lang={lang} t={t} />
        </section>
        <section className="admin-quick-actions">
          <Link to="/register"><span>＋</span><strong>{t("admin.quickRegister")}</strong><small>{t("admin.quickRegisterSub")}</small></Link>
          <Link to="/verify"><span>⌕</span><strong>{t("admin.quickVerify")}</strong><small>{t("admin.quickVerifySub")}</small></Link>
          <Link to="/flagged"><span>!</span><strong>{t("admin.quickFlagged")}</strong><small>{t("admin.quickFlaggedSub")}</small></Link>
          <Link to="/plot"><span>⌖</span><strong>{t("admin.quickPlot")}</strong><small>{t("admin.quickPlotSub")}</small></Link>
        </section>
      </>}

      {tab === "activity" && <section className="card admin-panel-card">
        <div className="admin-section-head"><div><h2>{t("admin.activityTitle")}</h2><p>{t("admin.activitySub", { n: num(audit.total) })}</p></div></div>
        <form className="admin-filterbar" onSubmit={searchAudit}>
          <input type="search" value={auditFilters.q} onChange={(e) => setAuditFilters({ ...auditFilters, q: e.target.value })} placeholder={t("admin.searchActivity")} aria-label={t("admin.searchActivity")} />
          <select value={auditFilters.action} onChange={(e) => setAuditFilters({ ...auditFilters, action: e.target.value })} aria-label={t("admin.actionFilter")}><option value="">{t("admin.allActions")}</option>{["deed.register","deed.mutation.completed","deed.flagged_list.view","deed.recent_list.view","deed.record.view","deed.qr_generated","land.plot_check","land.chain.verify","land.plot_location_updated","verification.paper_copy","verification.qr","assistant.explain","assistant.plot_question","assistant.deed_extract","system.demo_seed","registrar.access.denied","admin.access.denied","admin.overview.view","admin.audit.export"].map(x => <option key={x} value={x}>{x}</option>)}</select>
          <select value={auditFilters.outcome} onChange={(e) => setAuditFilters({ ...auditFilters, outcome: e.target.value })} aria-label={t("admin.outcomeFilter")}><option value="">{t("admin.allOutcomes")}</option>{["ok","registered","blocked","green","amber","red","denied"].map(x => <option key={x} value={x}>{x.toUpperCase()}</option>)}</select>
          <button className="btn btn-primary" type="submit">⌕ {t("admin.search")}</button>
        </form>
        <AuditTable items={audit.items} lang={lang} t={t} />
        <Pagination data={audit} onMore={() => loadAudit(key, audit.page + 1, true, auditFilters)} t={t} />
      </section>}

      {tab === "deeds" && <section className="card admin-panel-card">
        <div className="admin-section-head"><div><h2>{t("admin.deedsTitle")}</h2><p>{t("admin.deedsSub", { n: num(deeds.total) })}</p></div></div>
        <form className="admin-filterbar" onSubmit={searchDeeds}>
          <input type="search" value={deedFilters.q} onChange={(e) => setDeedFilters({ ...deedFilters, q: e.target.value })} placeholder={t("admin.searchDeeds")} aria-label={t("admin.searchDeeds")} />
          <select value={deedFilters.status} onChange={(e) => setDeedFilters({ ...deedFilters, status: e.target.value })}><option value="">{t("admin.allStatuses")}</option><option value="REGISTERED">REGISTERED</option><option value="BLOCKED">BLOCKED</option></select>
          <select value={deedFilters.risk} onChange={(e) => setDeedFilters({ ...deedFilters, risk: e.target.value })}><option value="">{t("admin.allRisks")}</option><option value="GREEN">GREEN</option><option value="AMBER">AMBER</option><option value="RED">RED</option></select>
          <select value={deedFilters.mutation} onChange={(e) => setDeedFilters({ ...deedFilters, mutation: e.target.value })}><option value="">{t("admin.allMutations")}</option><option value="PENDING">PENDING</option><option value="DONE">DONE</option><option value="NA">NA</option></select>
          <button className="btn btn-primary" type="submit">⌕ {t("admin.search")}</button>
        </form>
        <DeedTable items={deeds.items} lang={lang} t={t} />
        <Pagination data={deeds} onMore={() => loadDeeds(key, deeds.page + 1, true, deedFilters)} t={t} />
      </section>}

      {tab === "plots" && <section className="card admin-panel-card">
        <div className="admin-section-head"><div><h2>{t("admin.plotsTitle")}</h2><p>{t("admin.plotsSub", { n: num(plots.total) })}</p></div></div>
        <form className="admin-filterbar" onSubmit={searchPlots}><input type="search" value={plotQuery} onChange={(e) => setPlotQuery(e.target.value)} placeholder={t("admin.searchPlots")} aria-label={t("admin.searchPlots")} /><button className="btn btn-primary" type="submit">⌕ {t("admin.search")}</button></form>
        <PlotTable items={plots.items} t={t} />
        <Pagination data={plots} onMore={() => loadPlots(key, plots.page + 1, true, plotQuery)} t={t} />
      </section>}

      {tab === "system" && overview && <section className="admin-two-col admin-system-grid">
        <section className="card admin-panel-card"><div className="admin-section-head"><div><h2>{t("admin.systemInfo")}</h2><p>{t("admin.systemInfoSub")}</p></div></div>
          <dl className="admin-system-list"><dt>{t("admin.version")}</dt><dd>{overview.version}</dd><dt>{t("admin.environment")}</dt><dd>{overview.services.environment}</dd><dt>{t("admin.database")}</dt><dd><Outcome value="up" /></dd><dt>{t("admin.cacheBackend")}</dt><dd>{overview.services.cache}</dd><dt>{t("admin.aiModel")}</dt><dd>{overview.services.ai_model || t("admin.fallback")}</dd><dt>{t("admin.signatureAlgorithm")}</dt><dd>{overview.services.signing_algorithm}</dd><dt>{t("admin.keyId")}</dt><dd className="mono">{overview.services.signing_key_id}</dd><dt>{t("admin.generatedAt")}</dt><dd>{safeDate(overview.generated_at, lang)}</dd></dl>
        </section>
        <section className="card admin-panel-card"><div className="admin-section-head"><div><h2>{t("admin.securityTitle")}</h2><p>{t("admin.securitySub")}</p></div></div>
          <ul className="admin-security-list"><li><strong>{t("admin.adminKeyTitle")}</strong><span>{t("admin.adminKeyBody")}</span></li><li><strong>{t("admin.registrarTitle")}</strong><span>{t("admin.registrarBody")}</span></li><li><strong>{t("admin.immutableTitle")}</strong><span>{t("admin.immutableBody")}</span></li><li><strong>{t("admin.demoNoticeTitle")}</strong><span>{overview.services.demo_data_enabled ? t("admin.demoDataOn") : t("admin.demoDataOff")}</span></li></ul>
        </section>
      </section>}
      <p className="admin-disclaimer">ⓘ {t("admin.disclaimer")}</p>
    </section>
  );
}

function Pagination({ data, onMore, t }) {
  if (!data || data.items.length >= data.total) return null;
  return <div className="admin-pagination"><span>{t("admin.showing", { shown: num(data.items.length), total: num(data.total) })}</span><button className="btn btn-ghost" onClick={onMore}>{t("admin.loadMore")}</button></div>;
}
function EmptyRows({ children, cols }) {
  return <tr><td colSpan={cols} className="admin-empty">{children}</td></tr>;
}
function AuditTable({ items = [], lang, t, compact = false }) {
  return <div className="admin-table-wrap"><table className="table admin-table"><thead><tr><th>{t("admin.when")}</th><th>{t("admin.actionCol")}</th><th>{t("admin.summaryCol")}</th><th>{t("admin.targetCol")}</th><th>{t("admin.outcomeCol")}</th>{!compact && <><th>{t("admin.actorCol")}</th><th>{t("admin.ipCol")}</th></>}</tr></thead><tbody>
    {!items.length ? <EmptyRows cols={compact ? 5 : 7}>{t("admin.noActivity")}</EmptyRows> : items.map(item => <tr key={item.id}><td className="admin-date-cell">{safeDate(item.created_at, lang)}</td><td><code className="admin-action-code">{item.action}</code></td><td className="admin-summary-cell">{item.summary}{item.details && Object.keys(item.details).length > 0 && <details className="admin-detail"><summary>{t("admin.details")}</summary><pre>{JSON.stringify(item.details, null, 2)}</pre></details>}</td><td>{item.entity_type}{item.entity_id ? <span className="muted small"> · {item.entity_id}</span> : ""}</td><td><Outcome value={item.outcome} /></td>{!compact && <><td>{item.actor_type}</td><td className="mono small">{item.client_ip || "—"}</td></>}</tr>)}
  </tbody></table></div>;
}
function DeedTable({ items = [], lang, t }) {
  return <div className="admin-table-wrap"><table className="table admin-table"><thead><tr><th>{t("admin.deedCol")}</th><th>{t("admin.plotCol")}</th><th>{t("admin.partiesCol")}</th><th>{t("admin.areaCol")}</th><th>{t("admin.statusCol")}</th><th>{t("admin.riskCol")}</th><th>{t("admin.mutationCol")}</th><th>{t("admin.createdCol")}</th></tr></thead><tbody>
    {!items.length ? <EmptyRows cols={8}>{t("admin.noDeeds")}</EmptyRows> : items.map(d => <tr key={d.deed_no}><td><strong>{d.deed_no}</strong><div className="mono admin-hash">{d.fingerprint?.slice(0, 12)}…</div></td><td><Link to={`/plot?mouza=${encodeURIComponent(d.mouza)}&dag=${d.dag}`}>{d.mouza}/{num(d.dag)}</Link></td><td>{d.seller} <span className="muted">→</span> {d.buyer}</td><td>{fmtArea(d.area)}</td><td><Outcome value={d.status.toLowerCase()} /></td><td><Outcome value={d.risk.toLowerCase()} /></td><td><Outcome value={d.mutation_status.toLowerCase()} /></td><td>{safeDate(d.created_at, lang)}</td></tr>)}
  </tbody></table></div>;
}
function PlotTable({ items = [], t }) {
  return <div className="admin-table-wrap"><table className="table admin-table"><thead><tr><th>{t("admin.plotCol")}</th><th>{t("admin.khatianCol")}</th><th>{t("admin.typeCol")}</th><th>{t("admin.areaCol")}</th><th>{t("admin.holdersCol")}</th><th>{t("admin.deedsCol")}</th><th>{t("admin.flagsCol")}</th><th>{t("admin.mapCol")}</th></tr></thead><tbody>
    {!items.length ? <EmptyRows cols={8}>{t("admin.noPlots")}</EmptyRows> : items.map(p => <tr key={p.id}><td><Link to={`/plot?mouza=${encodeURIComponent(p.mouza)}&dag=${p.dag}`}><strong>{p.mouza}/{num(p.dag)}</strong></Link></td><td>{p.khatian_no || "—"}</td><td>{p.land_type}</td><td>{fmtArea(p.total_area)}</td><td>{num(p.holder_count)}</td><td>{num(p.deed_count)}</td><td><div className="admin-flag-list">{p.has_bank_lien && <Outcome value="lien" />}{p.has_court_case && <Outcome value="court" />}{p.is_khas && <Outcome value="khas" />}{!p.has_bank_lien && !p.has_court_case && !p.is_khas && <span className="muted">—</span>}</div></td><td>{p.latitude != null && p.longitude != null ? <a href={`https://www.google.com/maps/search/?api=1&query=${p.latitude},${p.longitude}`} target="_blank" rel="noreferrer">{t("admin.openMap")} ↗</a> : "—"}</td></tr>)}
  </tbody></table></div>;
}
