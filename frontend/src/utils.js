import { getLang, t } from "./strings.js";

const BN = "০১২৩৪৫৬৭৮৯";

/** Digits follow the active language (Bangla digits only when the UI is Bangla). */
export const num = (value) => {
  const s = String(value);
  return getLang() === "bn" ? s.replace(/\d/g, (d) => BN[Number(d)]) : s;
};
export const toBn = num; // kept for older imports

export const fmtArea = (value) => {
  const n = Number(value);
  return num(Number.isInteger(n) ? n : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, ""));
};

export const fmtDate = (iso) => {
  if (!iso) return "";
  const [y, m, d] = String(iso).slice(0, 10).split("-");
  return num(`${d}/${m}/${y}`);
};

export const todayIso = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

export const shortHash = (hash) => (hash ? `${hash.slice(0, 10)}…${hash.slice(-6)}` : "—");

/** Understands the QR link, a JSON payload, or a bare deed number. */
export function parseQr(text) {
  const raw = (text || "").trim();
  try {
    const url = new URL(raw);
    const deed = url.searchParams.get("deed");
    if (deed) return { deed: deed.toUpperCase(), hash: url.searchParams.get("hash") || "" };
  } catch {
    /* not a URL */
  }
  try {
    const json = JSON.parse(raw);
    const deed = json.deed || json.deed_no;
    if (deed) return { deed: String(deed).toUpperCase(), hash: json.hash || "" };
  } catch {
    /* not JSON */
  }
  if (/^D-\d+$/i.test(raw)) return { deed: raw.toUpperCase(), hash: "" };
  return null;
}

/** Reads "23.81, 90.41", a Google Maps URL (@lat,lng or ?q=lat,lng or !3d..!4d..) → {lat, lng} or null. */
export function parseLatLng(text) {
  let raw = (text || "").trim();
  try {
    raw = decodeURIComponent(raw);
  } catch {
    /* keep the raw text if it is not valid percent-encoding */
  }
  const bang = raw.match(/!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/);
  const pair = bang || raw.match(/(-?\d{1,3}(?:\.\d+)?)\s*[,\s]\s*(-?\d{1,3}(?:\.\d+)?)/);
  if (!pair) return null;
  const lat = Number(pair[1]);
  const lng = Number(pair[2]);
  return validLatLng(lat, lng) ? { lat, lng } : null;
}

export const validLatLng = (lat, lng) =>
  Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;

export const mapsEmbedUrl = (lat, lng) =>
  `https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lng}`)}&z=17&output=embed`;
/** Keyless, always-embeddable fallback (OpenStreetMap). */
export const osmEmbedUrl = (lat, lng) => {
  const la = Number(lat);
  const ln = Number(lng);
  const d = 0.003;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${ln - d},${la - d},${ln + d},${la + d}&layer=mapnik&marker=${la},${ln}`;
};
export const mapsOpenUrl = (lat, lng) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lat},${lng}`)}`;
export const mapsDirectionsUrl = (lat, lng) =>
  `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${lat},${lng}`)}`;

export const STATUS = {
  GREEN: { cls: "green", icon: "✓" },
  AMBER: { cls: "amber", icon: "!" },
  RED: { cls: "red", icon: "✕" },
};
export const statusLabel = (status) => t(`status.${status}`);
