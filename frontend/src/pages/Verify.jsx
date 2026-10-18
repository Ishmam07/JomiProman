import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import AiExplain from "../components/AiExplain.jsx";
import QrScanner from "../components/QrScanner.jsx";
import { ChecksList, ErrorBox, FindingList, Spinner, StatusBanner } from "../components/common.jsx";
import { fmtArea, fmtDate, parseQr, shortHash, todayIso } from "../utils.js";

const EMPTY = { deed_no: "", mouza: "", dag: "", seller: "", buyer: "", area: "", deed_date: todayIso(), hash: "" };

export default function Verify() {
  const { t } = useApp();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState(params.get("deed") ? "qr" : "copy");
  const [form, setForm] = useState(EMPTY);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (fn) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await fn());
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Opened from a QR code link: /verify?deed=D-0003&hash=...
  const qrDeed = params.get("deed");
  const qrHash = params.get("hash");
  useEffect(() => {
    if (qrDeed) run(() => api.verifyQr(qrDeed, qrHash));
  }, [qrDeed, qrHash, run]);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  function submitCopy(e) {
    e.preventDefault();
    run(() => api.verifyCopy({ ...form, dag: Number(form.dag), area: Number(form.area), hash: form.hash || null }));
  }

  function onScanned(text) {
    const parsed = parseQr(text);
    if (!parsed) {
      setError({ message: t("verify.notOurQr") });
      return;
    }
    setParams({ deed: parsed.deed, ...(parsed.hash ? { hash: parsed.hash } : {}) });
  }

  function loadFromLedger() {
    const no = form.deed_no.trim();
    if (!no) return setError({ message: t("verify.needNo") });
    setError(null);
    api
      .deed(no)
      .then((d) =>
        setForm({
          deed_no: d.deed_no, mouza: d.mouza, dag: String(d.dag), seller: d.seller, buyer: d.buyer,
          area: String(d.area), deed_date: d.deed_date, hash: d.fingerprint,
        })
      )
      .catch(setError);
  }

  return (
    <>
      <h1 className="page-title">{t("verify.title")}</h1>
      <p className="muted">{t("verify.sub")}</p>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "copy"} className={tab === "copy" ? "on" : ""} onClick={() => setTab("copy")}>
          {t("verify.tabCopy")}
        </button>
        <button role="tab" aria-selected={tab === "qr"} className={tab === "qr" ? "on" : ""} onClick={() => setTab("qr")}>
          {t("verify.tabQr")}
        </button>
      </div>

      {tab === "qr" && (
        <section className="card">
          <QrScanner onResult={onScanned} />
          <p className="muted small">{t("verify.qrHelp")}</p>
        </section>
      )}

      {tab === "copy" && (
        <form className="card form" onSubmit={submitCopy}>
          <div className="grid2">
            <label>
              {t("f.deedNo")}
              <input required value={form.deed_no} onChange={set("deed_no")} placeholder="D-0003" />
            </label>
            <label>
              {t("f.deedDate")}
              <input required type="date" value={form.deed_date} onChange={set("deed_date")} />
            </label>
            <label>
              {t("f.mouza")}
              <input required value={form.mouza} onChange={set("mouza")} placeholder={t("ph.mouza")} />
            </label>
            <label>
              {t("f.dag")}
              <input required inputMode="numeric" value={form.dag} onChange={set("dag")} placeholder="412" />
            </label>
            <label>
              {t("f.seller")}
              <input required value={form.seller} onChange={set("seller")} placeholder={t("ph.seller")} />
            </label>
            <label>
              {t("f.buyer")}
              <input required value={form.buyer} onChange={set("buyer")} placeholder={t("ph.buyer")} />
            </label>
            <label>
              {t("f.areaVerify")}
              <input required inputMode="decimal" value={form.area} onChange={set("area")} placeholder="6" />
            </label>
            <label>
              {t("f.hash")}
              <input value={form.hash} onChange={set("hash")} placeholder={t("f.hashPh")} />
            </label>
          </div>
          <div className="row">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {t("verify.run")}
            </button>
            <button type="button" className="btn btn-ghost" onClick={loadFromLedger}>
              {t("verify.fill")}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => { setForm(EMPTY); setResult(null); setError(null); }}>
              {t("clear")}
            </button>
          </div>
          <p className="muted small">
            {t("verify.tip")}
          </p>
        </form>
      )}

      {loading && <Spinner />}
      <ErrorBox error={error} />

      {result && (
        <div className="result">
          <StatusBanner status={result.status} title={result.headline} />
          <FindingList findings={result.findings} />
          <ChecksList checks={result.checks} />

          {result.changes.length > 0 && (
            <section className="card">
              <h3>{t("verify.changes")}</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("verify.col.field")}</th>
                    <th>{t("verify.col.ledger")}</th>
                    <th>{t("verify.col.copy")}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.changes.map((c) => (
                    <tr key={c.field}>
                      <td>{c.label}</td>
                      <td className="ok-text">{c.stored}</td>
                      <td className="bad-text">{c.provided}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {result.deed && (
            <section className="card">
              <h3>{t("verify.record")} {result.deed.deed_no}</h3>
              <dl className="kv">
                <dt>{t("verify.mouzaDag")}</dt>
                <dd>{result.deed.mouza} / {result.deed.dag}</dd>
                <dt>{t("verify.sellerBuyer")}</dt>
                <dd>{result.deed.seller} → {result.deed.buyer}</dd>
                <dt>{t("verify.area")}</dt>
                <dd>{fmtArea(result.deed.area)} {t("shatangsha")}</dd>
                <dt>{t("verify.date")}</dt>
                <dd>{fmtDate(result.deed.deed_date)}</dd>
                <dt>{t("verify.fp")}</dt>
                <dd className="mono">{shortHash(result.deed.fingerprint)}</dd>
                <dt>{t("verify.mutation")}</dt>
                <dd>{t(`mut.${result.deed.mutation_status}`)}</dd>
              </dl>
            </section>
          )}

          <AiExplain status={result.status} findings={result.findings} />
        </div>
      )}
    </>
  );
}
