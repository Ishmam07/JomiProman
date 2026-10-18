import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import { mapsDirectionsUrl, mapsOpenUrl, osmEmbedUrl, parseLatLng, validLatLng } from "../utils.js";
import { ErrorBox } from "./common.jsx";

const KEY_STORAGE = "jomiproman.registrarKey";
function loadKey() {
  try {
    return sessionStorage.getItem(KEY_STORAGE) || "demo-registrar";
  } catch {
    return "demo-registrar";
  }
}

/** Google Maps view of a plot, plus a registrar form to add/change its latitude & longitude. */
export default function MapPanel({ mouza, dag, latitude, longitude, address, onSaved, startEditing = false }) {
  const { t } = useApp();
  const has = latitude != null && longitude != null;
  const [editing, setEditing] = useState(startEditing && !has);
  const [lat, setLat] = useState(has ? String(latitude) : "");
  const [lng, setLng] = useState(has ? String(longitude) : "");
  const [addr, setAddr] = useState(address || "");
  const [paste, setPaste] = useState("");
  const [key, setKey] = useState(loadKey);
  const [busy, setBusy] = useState(false);
  const [gpsBusy, setGpsBusy] = useState(false);
  const [error, setError] = useState(null);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    setLat(has ? String(latitude) : "");
    setLng(has ? String(longitude) : "");
    setAddr(address || "");
    setEditing(startEditing && !has);
    setError(null);
    setOk(false);
  }, [mouza, dag, latitude, longitude, address]); // eslint-disable-line react-hooks/exhaustive-deps

  const nLat = Number(lat);
  const nLng = Number(lng);
  const draftOk = lat !== "" && lng !== "" && validLatLng(nLat, nLng);

  function readPaste() {
    const p = parseLatLng(paste);
    if (!p) return setError({ message: t("map.pasteBad") });
    setError(null);
    setLat(String(p.lat));
    setLng(String(p.lng));
  }

  function useGps() {
    if (!navigator.geolocation) return setError({ message: t("map.gpsNo") });
    setGpsBusy(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLng(pos.coords.longitude.toFixed(6));
        setGpsBusy(false);
      },
      () => {
        setGpsBusy(false);
        setError({ message: t("map.gpsErr") });
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  }

  async function save(e) {
    e.preventDefault();
    setError(null);
    setOk(false);
    if (!draftOk) return setError({ message: t("map.range") });
    setBusy(true);
    try {
      const view = await api.setLocation(mouza, dag, { latitude: nLat, longitude: nLng, address: addr.trim() || null }, key);
      try {
        sessionStorage.setItem(KEY_STORAGE, key);
      } catch {
        /* storage unavailable */
      }
      setOk(true);
      setEditing(false);
      onSaved?.(view);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const shownLat = editing && draftOk ? nLat : latitude;
  const shownLng = editing && draftOk ? nLng : longitude;
  const showMap = shownLat != null && shownLng != null;

  return (
    <section className="card map-card">
      <div className="card-head">
        <h3>📍 {t("map.title")}</h3>
        {!editing && (
          <button type="button" className="link-btn" onClick={() => setEditing(true)}>
            {t("map.edit")}
          </button>
        )}
      </div>

      {showMap ? (
        <>
          <iframe
            className="map-frame"
            title={t("map.frame")}
            src={osmEmbedUrl(shownLat, shownLng)}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            allowFullScreen
          />
          <p className="muted small mono-line">
            {Number(shownLat).toFixed(6)}, {Number(shownLng).toFixed(6)}
            {(editing ? addr : address) ? ` · ${editing ? addr : address}` : ""}
          </p>
          <div className="row">
            <a className="btn btn-ghost" href={mapsOpenUrl(shownLat, shownLng)} target="_blank" rel="noreferrer">
              {t("map.open")}
            </a>
            <a className="btn btn-ghost" href={mapsDirectionsUrl(shownLat, shownLng)} target="_blank" rel="noreferrer">
              {t("map.directions")}
            </a>
          </div>
        </>
      ) : (
        <p className="muted">{t("map.none")}</p>
      )}

      {ok && !editing && <div className="alert alert-green">{t("map.saved")}</div>}

      {editing && (
        <form className="form map-form" onSubmit={save}>
          <label>
            {t("map.paste")}
            <span className="inline-row">
              <input value={paste} onChange={(e) => setPaste(e.target.value)} placeholder="23.8103, 90.4125" />
              <button type="button" className="btn btn-ghost" onClick={readPaste} disabled={!paste.trim()}>
                {t("map.pasteBtn")}
              </button>
            </span>
          </label>
          <div className="grid2">
            <label>
              {t("map.lat")}
              <input required inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="23.8103" />
            </label>
            <label>
              {t("map.lng")}
              <input required inputMode="decimal" value={lng} onChange={(e) => setLng(e.target.value)} placeholder="90.4125" />
            </label>
          </div>
          <label>
            {t("map.address")}
            <input value={addr} maxLength={200} onChange={(e) => setAddr(e.target.value)} />
          </label>
          <label>
            {t("map.key")}
            <input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
          </label>
          <div className="row">
            <button type="button" className="btn btn-ghost" onClick={useGps} disabled={gpsBusy}>
              {gpsBusy ? t("map.gpsBusy") : `🎯 ${t("map.gps")}`}
            </button>
            <button className="btn btn-primary" disabled={busy || !draftOk}>
              {t("map.save")}
            </button>
            {has && (
              <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>
                {t("map.cancel")}
              </button>
            )}
          </div>
        </form>
      )}
      <ErrorBox error={error} />
    </section>
  );
}
