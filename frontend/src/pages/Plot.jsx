import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import MapPanel from "../components/MapPanel.jsx";
import AiExplain from "../components/AiExplain.jsx";
import PlotChat from "../components/PlotChat.jsx";
import { Chip, ErrorBox, FindingList, Spinner, StatusBanner } from "../components/common.jsx";
import { fmtArea, fmtDate, num } from "../utils.js";

export default function Plot() {
  const { t } = useApp();
  const [params, setParams] = useSearchParams();
  const [plots, setPlots] = useState([]);
  const [mouza, setMouza] = useState(params.get("mouza") || "");
  const [dag, setDag] = useState(params.get("dag") || "");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.plots().then(setPlots).catch(() => {});
  }, []);

  const load = useCallback(async (m, d) => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      setData(await api.plot(m, d));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const qMouza = params.get("mouza");
  const qDag = params.get("dag");
  useEffect(() => {
    if (qMouza && qDag) load(qMouza, qDag);
  }, [qMouza, qDag, load]);

  function submit(e) {
    e.preventDefault();
    setParams({ mouza: mouza.trim(), dag: dag.trim() });
  }

  const mouzas = [...new Set(plots.map((p) => p.mouza))];

  return (
    <>
      <h1 className="page-title">{t("plot.title")}</h1>
      <p className="muted">{t("plot.sub")}</p>

      <form className="card form" onSubmit={submit}>
        <div className="grid2">
          <label>
            {t("f.mouza")}
            <input required list="mouza-list" value={mouza} onChange={(e) => setMouza(e.target.value)} placeholder={t("ph.mouza")} />
            <datalist id="mouza-list">
              {mouzas.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </label>
          <label>
            {t("f.dag")}
            <input required inputMode="numeric" value={dag} onChange={(e) => setDag(e.target.value)} placeholder="412" />
          </label>
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {t("verify.run")}
        </button>
        {plots.length > 0 && (
          <div className="chips">
            <span className="muted small">{t("plot.demo")}</span>
            {plots.map((p) => (
              <button
                type="button"
                key={`${p.mouza}-${p.dag}`}
                className="chip-btn"
                onClick={() => {
                  setMouza(p.mouza);
                  setDag(String(p.dag));
                  setParams({ mouza: p.mouza, dag: String(p.dag) });
                }}
              >
                {p.mouza} / {num(p.dag)}
              </button>
            ))}
          </div>
        )}
      </form>

      {loading && <Spinner />}
      <ErrorBox error={error} />

      {data && (
        <div className="result">
          <StatusBanner status={data.status} title={data.headline}>
            {data.advice}
          </StatusBanner>
          <FindingList findings={data.findings} />

          <section className="card">
            <h3>
              {data.mouza}, {t("plot.dag")} {num(data.dag)}
            </h3>
            <dl className="kv">
              <dt>{t("plot.total")}</dt>
              <dd>{fmtArea(data.total_area)} {t("shatangsha")}</dd>
              <dt>{t("plot.type")}</dt>
              <dd>{data.land_type}</dd>
              <dt>{t("plot.khatian")}</dt>
              <dd>{data.khatian_no || "—"}</dd>
              <dt>{t("plot.chain")}</dt>
              <dd>
                {data.chain.valid ? (
                  <Chip status="GREEN">{t("plot.intact", { n: num(data.chain.length) })}</Chip>
                ) : (
                  <Chip status="RED">{t("plot.broken", { n: data.chain.broken_deed_no })}</Chip>
                )}
              </dd>
            </dl>
          </section>

          <section className="card">
            <h3>{t("plot.owners")}</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>{t("plot.col.name")}</th>
                  <th>{t("plot.col.area")}</th>
                  <th>{t("plot.col.mut")}</th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.holder}>
                    <td>{h.holder}</td>
                    <td>{fmtArea(h.area)}</td>
                    <td>{h.mutated ? <Chip status="GREEN">{t("mut.DONE")}</Chip> : <Chip status="AMBER">{t("mut.PENDING")}</Chip>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>{t("plot.history")}</h3>
            {data.history.length === 0 ? (
              <p className="muted">{t("plot.noHistory")}</p>
            ) : (
              <ol className="timeline">
                {data.history.map((h) => (
                  <li key={h.deed_no} className={`tl tl-${h.status === "BLOCKED" ? "red" : h.risk === "AMBER" ? "amber" : "green"}`}>
                    <div className="tl-top">
                      <strong>{h.deed_no}</strong>
                      {h.status === "BLOCKED" ? <Chip status="RED">{t("plot.blocked")}</Chip> : <Chip status={h.risk}>{t("plot.registered")}</Chip>}
                    </div>
                    <div>
                      {h.seller} → {h.buyer} · {fmtArea(h.area)} {t("shatangsha")} · {fmtDate(h.deed_date)}
                    </div>
                    {h.status !== "BLOCKED" && <div className="muted small">{t("plot.mutLabel")} {t(`mut.${h.mutation_status}`)}</div>}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <MapPanel
            mouza={data.mouza}
            dag={data.dag}
            latitude={data.latitude}
            longitude={data.longitude}
            address={data.address}
            onSaved={setData}
          />

          <AiExplain status={data.status} findings={data.findings} />
          <PlotChat mouza={data.mouza} dag={data.dag} />
        </div>
      )}
    </>
  );
}
