// Central API client. Same-origin by default (works behind /api rewrites
// in production); set VITE_API_URL for local dev against :8000 directly
// (vite.config.js also proxies /api to the backend during npm run dev).
export const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  devices: () => request("/api/devices"),
  device: (id) => request(`/api/devices/${id}`),
  createDevice: (payload) =>
    request("/api/devices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  configurations: () => request("/api/configurations"),
  upload: (file, deviceName) => {
    const form = new FormData();
    form.append("file", file);
    if (deviceName) form.append("device_name", deviceName);
    return request("/api/configurations/upload", { method: "POST", body: form });
  },
  audits: (limit = 50) => request(`/api/audits?limit=${limit}`),
  audit: (id) => request(`/api/audits/${id}`),
  runAudit: (configurationId) =>
    request("/api/audits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ configuration_id: configurationId }),
    }),
  results: (auditId) => request(`/api/results/${auditId}`),
  rules: () => request("/api/rules"),
  mappings: (status) =>
    request(status ? `/api/mappings?status=${status}` : "/api/mappings"),
  createMapping: (payload) =>
    request("/api/mappings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  reviewMapping: (id, payload) =>
    request(`/api/mappings/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  resolveMapping: (vendor, rawPattern) =>
    request("/api/mappings/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vendor, raw_pattern: rawPattern }),
    }),
  aiAnalyze: (text, vendor = "unknown") =>
    request("/api/ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, vendor }),
    }),
  aiExplain: (payload) =>
    request("/api/ai/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  detect: (text) =>
    request("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
};
