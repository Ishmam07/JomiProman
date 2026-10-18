// Thin fetch wrapper around the backend. Every error becomes an ApiError with a readable message.
import { t } from "./strings.js";

const BASE = import.meta.env.VITE_API_BASE || "/api";

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, { method = "GET", body, headers = {} } = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(t("err.network"), 0, "network");
  }
  if (!res.ok) {
    let message = t("err.server");
    let code;
    try {
      const data = await res.json();
      message = data?.error?.message || message;
      code = data?.error?.code;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status, code);
  }
  return res.json();
}

const enc = encodeURIComponent;
const registrar = (key) => ({ "X-Registrar-Key": key });

export const api = {
  stats: () => request("/stats"),
  plots: () => request("/plots"),
  plot: (mouza, dag) => request(`/plots/${enc(mouza)}/${enc(dag)}`),
  setLocation: (mouza, dag, body, key) =>
    request(`/plots/${enc(mouza)}/${enc(dag)}/location`, { method: "PUT", body, headers: registrar(key) }),
  deed: (no) => request(`/deeds/${enc(no)}`),
  flagged: () => request("/deeds/flagged"),
  verifyCopy: (body) => request("/verify", { method: "POST", body }),
  verifyQr: (no, hash) => request(`/verify/${enc(no)}${hash ? `?hash=${enc(hash)}` : ""}`),
  registerDeed: (body, key) => request("/deeds", { method: "POST", body, headers: registrar(key) }),
  completeMutation: (no, key) =>
    request(`/deeds/${enc(no)}/mutation`, { method: "POST", headers: registrar(key) }),
  explain: (status, findings) =>
    request("/assistant/explain", {
      method: "POST",
      body: { status, findings: findings.map(({ code, message }) => ({ code, message })) },
    }),
  ask: (mouza, dag, question) =>
    request("/assistant/ask", { method: "POST", body: { mouza, dag: Number(dag), question } }),
  extract: (text) => request("/assistant/extract", { method: "POST", body: { text } }),
  // Admin calls always carry the separate X-Admin-Key. The key is held in sessionStorage only.
  adminOverview: (key) => request("/admin/overview", { headers: { "X-Admin-Key": key } }),
  adminAudit: (key, params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)).toString();
    return request(`/admin/audit${qs ? `?${qs}` : ""}`, { headers: { "X-Admin-Key": key } });
  },
  adminDeeds: (key, params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)).toString();
    return request(`/admin/deeds${qs ? `?${qs}` : ""}`, { headers: { "X-Admin-Key": key } });
  },
  adminPlots: (key, params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)).toString();
    return request(`/admin/plots${qs ? `?${qs}` : ""}`, { headers: { "X-Admin-Key": key } });
  },
  adminAuditCsv: async (key) => {
    const res = await fetch(`${BASE}/admin/audit.csv`, { headers: { "X-Admin-Key": key } });
    if (!res.ok) {
      let message = t("err.server");
      try { message = (await res.json())?.error?.message || message; } catch { /* not JSON */ }
      throw new ApiError(message, res.status, "admin_export_failed");
    }
    return res.blob();
  },
};
