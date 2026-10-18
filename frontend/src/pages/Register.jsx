import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import MapPanel from "../components/MapPanel.jsx";
import AiExplain from "../components/AiExplain.jsx";
import { ErrorBox, FindingList, Spinner, StatusBanner } from "../components/common.jsx";
import { fmtArea, num, shortHash, todayIso } from "../utils.js";

const EMPTY = { mouza: "রহিমপুর", dag: "412", seller: "", buyer: "", area: "", deed_date: todayIso() };
const KEY_STORAGE = "jomiproman.registrarKey";

function loadKey() {
  try {
    return sessionStorage.getItem(KEY_STORAGE) || "demo-registrar";
  } catch {
    return "demo-registrar";
  }
}

const SAMPLE = `মৌজা: রহিমপুর
দাগ নং: ৪১২
বিক্রেতা: করিম
ক্রেতা: রফিক
জমির পরিমাণ: ৬ শতাংশ
তারিখ: ১৭/১০/২০২৬`; // the extractor understands Bangla deed text

export default function Register() {
  const { t } = useApp();
  const [plotView, setPlotView] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [key, setKey] = useState(loadKey);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [text, setText] = useState("");
  const [extractNote, setExtractNote] = useState(null);
  const [extracting, setExtracting] = useState(false);

  useEffect(() => {
    try {
      sessionStorage.setItem(KEY_STORAGE, key);
    } catch {
      /* storage unavailable */
    }
  }, [key]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.registerDeed({ ...form, dag: Number(form.dag), area: Number(form.area) }, key));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  async function extract() {
    setExtracting(true);
    setExtractNote(null);
    setError(null);
    try {
      const r = await api.extract(text);
      const f = r.fields;
      setForm((cur) => ({
        ...cur,
        ...(f.mouza ? { mouza: f.mouza } : {}),
        ...(f.dag ? { dag: String(f.dag) } : {}),
        ...(f.seller ? { seller: f.seller } : {}),
        ...(f.buyer ? { buyer: f.buyer } : {}),
        ...(f.area ? { area: String(f.area) } : {}),
        ...(f.deed_date ? { deed_date: f.deed_date } : {}),
      }));
      setExtractNote(r);
    } catch (err) {
      setError(err);
    } finally {
      setExtracting(false);
    }
  }

  // After a successful registration, load the plot so its map location can be added right away.
  useEffect(() => {
    setPlotView(null);
    if (!result || result.status !== "REGISTERED") return;
    api.plot(result.mouza, result.dag).then(setPlotView).catch(() => {});
  }, [result?.deed_no, result?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function completeMutation() {
    try {
      const updated = await api.completeMutation(result.deed_no, key);
      setResult(updated);
    } catch (err) {
      setError(err);
    }
  }

  const registered = result?.status === "REGISTERED";

  return (
    <>
      <h1 className="page-title">{t("reg.title")}</h1>
      <p className="muted">
        {t("reg.sub")}
      </p>

      <section className="card">
        <div className="card-head">
          <h3>{t("reg.aiTitle")}</h3>
          <button type="button" className="link-btn" onClick={() => setText(SAMPLE)}>
            {t("reg.sample")}
          </button>
        </div>
        <textarea
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={4000}
          placeholder={t("reg.aiPh")}
        />
        <div className="row">
          <button type="button" className="btn btn-ghost" onClick={extract} disabled={extracting || text.trim().length < 5}>
            {t("reg.extract")}
          </button>
          {extracting && <Spinner label={t("reg.reading")} />}
        </div>
        {extractNote && (
          <div className={`alert ${extractNote.missing.length ? "alert-amber" : "alert-green"}`}>
            {extractNote.note}
            {extractNote.missing.length > 0 && <>{t("reg.fillRest")}</>}
          </div>
        )}
      </section>

      <form className="card form" onSubmit={submit}>
        <div className="grid2">
          <label>
            {t("f.mouza")}
            <input required value={form.mouza} onChange={set("mouza")} />
          </label>
          <label>
            {t("f.dag")}
            <input required inputMode="numeric" value={form.dag} onChange={set("dag")} />
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
            {t("f.areaSell")}
            <input required inputMode="decimal" value={form.area} onChange={set("area")} placeholder="6" />
          </label>
          <label>
            {t("f.deedDate")}
            <input required type="date" value={form.deed_date} onChange={set("deed_date")} />
          </label>
        </div>
        <label>
          {t("reg.key")}
          <input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
        </label>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {t("reg.submit")}
        </button>
      </form>

      {loading && <Spinner />}
      <ErrorBox error={error} />

      {result && (
        <div className="result">
          <StatusBanner
            status={result.risk}
            title={registered ? t("reg.done", { n: result.deed_no }) : t("reg.blockedTitle", { n: result.deed_no })}
          >
            {registered
              ? result.risk === "AMBER"
                ? t("reg.okAmber")
                : t("reg.okGreen")
              : t("reg.blockedMsg")}
          </StatusBanner>
          <FindingList findings={result.findings} />

          {registered && (
            <section className="card qr-card">
              <img src={result.qr_image_url} alt={t("reg.qrAlt", { n: result.deed_no })} width="190" height="190" />
              <div>
                <h3>{t("reg.qrTitle")}</h3>
                <p className="muted">{t("reg.qrHelp")}</p>
                <dl className="kv">
                  <dt>{t("verify.fp")}</dt>
                  <dd className="mono">{shortHash(result.fingerprint)}</dd>
                  <dt>{t("reg.chainNo")}</dt>
                  <dd>#{num(result.chain_index)}</dd>
                  <dt>{t("verify.area")}</dt>
                  <dd>{fmtArea(result.area)} {t("shatangsha")}</dd>
                </dl>
                <div className="row">
                  <Link className="btn btn-ghost" to={`/verify?deed=${result.deed_no}&hash=${result.fingerprint}`}>
                    {t("reg.openVerify")}
                  </Link>
                  {result.mutation_status === "PENDING" && (
                    <button type="button" className="btn btn-ghost" onClick={completeMutation}>
                      {t("reg.doMutation")}
                    </button>
                  )}
                  <button type="button" className="btn btn-ghost" onClick={() => window.print()}>
                    {t("reg.print")}
                  </button>
                  {result.mutation_status === "DONE" && <span className="chip chip-green">{t("reg.mutDone")}</span>}
                </div>
              </div>
            </section>
          )}

          {registered && plotView && (
            <MapPanel
              mouza={plotView.mouza}
              dag={plotView.dag}
              latitude={plotView.latitude}
              longitude={plotView.longitude}
              address={plotView.address}
              onSaved={setPlotView}
            />
          )}

          <AiExplain status={result.risk} findings={result.findings} />
        </div>
      )}
    </>
  );
}
