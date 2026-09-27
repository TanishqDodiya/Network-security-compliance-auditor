// Analyst review queue for unknown configuration syntax.
// Flow: unknown line → stored mapping or AI suggestion → human
// confirm/reject → stored mapping reused on repeat sightings.
import { useState } from "react";
import Badge from "../components/Badge.jsx";
import { Alert, Card, EmptyState, ErrorState, LoadingState, PageHeader, SectionTitle } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api } from "../services/api.js";

const CATEGORIES = ["Authentication", "Management Security", "Logging", "Network Security", "System", "Other"];

const STEPS = ["Unknown line", "Suggested interpretation", "Human review", "Stored mapping"];

export default function Mappings() {
  const { data, loading, error, reload } = useFetch(() => api.mappings());
  const [vendor, setVendor] = useState("juniper");
  const [pattern, setPattern] = useState("set xyz secure-admin-mode enabled");
  const [suggestion, setSuggestion] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [confirmBy, setConfirmBy] = useState("admin");

  async function handleResolve(e) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    setSuggestion(null);
    try {
      setSuggestion(await api.resolveMapping(vendor, pattern));
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveMapping(source) {
    // Save AI suggestion as pending for review.
    setBusy(true);
    setMsg("");
    try {
      if (source === "ai" && suggestion) {
        const created = await api.createMapping({
          vendor,
          raw_pattern: pattern,
          normalized_field: suggestion.suggested_field || "",
          suggested_category: suggestion.suggested_category || "Other",
          confidence: suggestion.confidence || 0,
          status: "pending",
          confirmed_by: "",
        });
        setMsg(`Saved as pending item #${created.id}. Review it in the queue below.`);
      }
      await reload();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function review(id, status, normalizedField, category) {
    setBusy(true);
    setMsg("");
    try {
      await api.reviewMapping(id, {
        status,
        normalized_field: normalizedField,
        suggested_category: category,
        confirmed_by: confirmBy || "admin",
      });
      setMsg(`Item #${id} marked as ${status}. Stored mappings are reused automatically.`);
      await reload();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  }

  const pending = (data || []).filter((m) => m.status === "pending").length;
  const confirmed = (data || []).filter((m) => m.status === "confirmed").length;

  return (
    <div className="max-w-3xl space-y-4">
      <PageHeader
        title="Unknown syntax review"
        description={`${pending} pending · ${confirmed} confirmed. Stored mappings are reused before AI is consulted.`}
      />

      <ol className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500" aria-label="Review workflow">
        {STEPS.map((s, i) => (
          <li key={s} className="flex items-center gap-1.5">
            {i > 0 && <span aria-hidden="true" className="text-slate-300">→</span>}
            <span className="px-2 py-1 rounded bg-white border border-slate-200 font-medium">{i + 1}. {s}</span>
          </li>
        ))}
      </ol>

      <Card>
        <SectionTitle>Analyze a configuration line</SectionTitle>
        <form onSubmit={handleResolve} aria-label="Analyze unknown configuration">
          <div className="grid sm:grid-cols-[160px_1fr] gap-3">
            <div>
              <label htmlFor="map-vendor" className="label">Vendor</label>
              <select id="map-vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} className="select">
                <option value="cisco">cisco</option>
                <option value="juniper">juniper</option>
                <option value="paloalto">paloalto</option>
                <option value="unknown">unknown</option>
              </select>
            </div>
            <div>
              <label htmlFor="map-pattern" className="label">Configuration line</label>
              <input
                id="map-pattern"
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                className="input font-mono"
              />
            </div>
          </div>
          <div className="mt-3">
            <button type="submit" disabled={busy} className="btn btn-primary">
              {busy && <span className="spinner" aria-hidden="true" />}
              {busy ? "Analyzing…" : "Analyze"}
            </button>
          </div>
        </form>

        {suggestion && (
          <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge value={suggestion.source === "stored" ? "Stored mapping" : "AI suggestion"} tone={suggestion.source === "stored" ? "badge-pass" : "badge-info"} />
              <span className="text-slate-500">
                Confidence {(Number(suggestion.confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <p className="font-medium text-slate-900">
              Suggested interpretation: {suggestion.suggested_category}
            </p>
            {suggestion.meaning && <p className="text-slate-600">{suggestion.meaning}</p>}
            <p className="text-slate-600">
              Normalized field: <code className="text-xs">{suggestion.suggested_field || "(none yet)"}</code>
            </p>
            {suggestion.source === "ai" ? (
              <button onClick={() => saveMapping("ai")} disabled={busy} className="btn btn-sm btn-secondary mt-1">
                Save for review
              </button>
            ) : (
              <p className="text-xs text-slate-500">{suggestion.message}</p>
            )}
          </div>
        )}
      </Card>

      {msg && <Alert kind={msg.startsWith("Item") || msg.startsWith("Saved") ? "ok" : "error"}>{msg}</Alert>}

      <Card>
        <SectionTitle>Review queue</SectionTitle>
        <div className="mb-3 max-w-xs">
          <label htmlFor="confirmed-by" className="label">Reviewer name</label>
          <input id="confirmed-by" value={confirmBy} onChange={(e) => setConfirmBy(e.target.value)} className="input" />
        </div>
        {loading && <LoadingState text="Loading mappings…" />}
        {error && <ErrorState message={error} onRetry={reload} />}
        {!loading && !error && (data || []).length === 0 && (
          <EmptyState text="No mappings yet. Analyze a line above to start the review workflow." />
        )}
        <div className="space-y-2.5">
          {(data || []).map((m) => (
            <MappingRow key={m.id} mapping={m} busy={busy} onReview={review} />
          ))}
        </div>
      </Card>
    </div>
  );
}

function MappingRow({ mapping: m, busy, onReview }) {
  const [field, setField] = useState(m.normalized_field || "");
  const [cat, setCat] = useState(m.suggested_category || "Other");
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge value={m.vendor} />
        <Badge value={m.status} />
        <code className="text-xs text-slate-700 break-all">{m.raw_pattern}</code>
      </div>
      <p className="text-xs text-slate-500">
        Suggestion: {m.suggested_category} → <code>{m.normalized_field || "(empty)"}</code> · {((m.confidence || 0) * 100).toFixed(0)}% confidence
      </p>
      <div className="flex gap-2 flex-wrap items-end">
        <div className="w-56 max-w-full">
          <label htmlFor={`map-field-${m.id}`} className="label">Normalized field</label>
          <input id={`map-field-${m.id}`} value={field} onChange={(e) => setField(e.target.value)} placeholder="management.example_setting" className="input font-mono" />
        </div>
        <div className="w-44 max-w-full">
          <label htmlFor={`map-cat-${m.id}`} className="label">Category</label>
          <select id={`map-cat-${m.id}`} value={cat} onChange={(e) => setCat(e.target.value)} className="select">
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="flex gap-2 pb-px">
          <button disabled={busy} onClick={() => onReview(m.id, "confirmed", field, cat)} className="btn btn-sm btn-primary">
            Confirm
          </button>
          <button disabled={busy} onClick={() => onReview(m.id, "rejected", field, cat)} className="btn btn-sm btn-danger">
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
