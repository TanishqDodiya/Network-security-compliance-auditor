// Settings: environment connections and diagnostics.
import { useState } from "react";
import { API_BASE, api } from "../services/api.js";
import { Alert, Card, PageHeader, SectionTitle } from "../components/ui.jsx";

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [ai, setAi] = useState(null);
  const [busy, setBusy] = useState("");

  async function checkBackend() {
    setBusy("backend");
    setHealth(null);
    try {
      await api.health();
      setHealth({ ok: true, text: "Backend is reachable." });
    } catch (e) {
      setHealth({ ok: false, text: `Unreachable: ${e.message}` });
    } finally {
      setBusy("");
    }
  }

  async function checkAi() {
    setBusy("ai");
    setAi(null);
    try {
      const out = await api.aiAnalyze("set xyz secure-admin-mode enabled", "juniper");
      setAi(out);
    } catch (e) {
      setAi({ error: e.message });
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <PageHeader
        title="Settings"
        description="Environment connections and service diagnostics."
      />

      <Card>
        <SectionTitle>Backend connection</SectionTitle>
        <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1.5 text-sm mb-3">
          <dt className="text-slate-500">Backend URL</dt>
          <dd className="mono text-slate-900 break-all">{API_BASE || "(same origin — /api on this domain)"}</dd>
          <dt className="text-slate-500">Configuration</dt>
          <dd className="text-slate-600">
            Override with <code className="text-xs">VITE_API_URL</code> in <code className="text-xs">frontend/.env</code>.
          </dd>
        </dl>
        <button onClick={checkBackend} disabled={busy === "backend"} className="btn btn-sm btn-secondary">
          {busy === "backend" ? "Checking…" : "Check connection"}
        </button>
        {health && (
          <div className="mt-3">
            <Alert kind={health.ok ? "ok" : "error"}>{health.text}</Alert>
          </div>
        )}
      </Card>

      <Card>
        <SectionTitle>AI assistance</SectionTitle>
        <p className="text-sm text-slate-600 mb-3">
          Set <code className="text-xs">AI_PROVIDER=openai</code> and{" "}
          <code className="text-xs">AI_API_KEY</code> in the backend <code className="text-xs">.env</code> for
          live language-model assistance. Without a key, the built-in deterministic
          analysis is used and audits continue to work.
        </p>
        <button onClick={checkAi} disabled={busy === "ai"} className="btn btn-sm btn-secondary">
          {busy === "ai" ? "Checking…" : "Check AI status"}
        </button>
        {ai && (
          <div className="mt-3 text-sm">
            {ai.error ? (
              <Alert kind="error">{ai.error}</Alert>
            ) : (
              <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1.5 rounded-md border border-slate-200 bg-slate-50 p-3">
                <dt className="text-slate-500">Provider</dt>
                <dd className="font-medium text-slate-900">{ai.provider}</dd>
                <dt className="text-slate-500">AI available</dt>
                <dd className="font-medium text-slate-900">{String(ai.ai_available)}</dd>
                <dt className="text-slate-500">Sample analysis</dt>
                <dd className="text-slate-600">{ai.suggested_category}</dd>
              </dl>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
