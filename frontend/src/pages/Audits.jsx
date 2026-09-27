// Audit runs + per-rule findings with evidence, remediation, AI explanation.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import Badge from "../components/Badge.jsx";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api } from "../services/api.js";
import { formatDate, pct } from "../utils/format.js";

export function Audits() {
  const { data, loading, error, reload } = useFetch(() => api.audits(100));
  const devices = useFetch(api.devices);
  if (loading) return <LoadingState text="Loading audits…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const nameById = Object.fromEntries(((devices.data || []).map((d) => [d.id, d.name])));
  return (
    <div className="space-y-4">
      <PageHeader
        title="Audits"
        description="Compliance runs across uploaded configurations."
      />
      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Audit</th>
                <th>Device</th>
                <th className="num">Compliance</th>
                <th>Finished</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/audits/${a.id}`} className="font-semibold text-blue-800 hover:underline">
                      Audit #{a.id}
                    </Link>
                  </td>
                  <td>{nameById[a.device_id] || `Device #${a.device_id}`}</td>
                  <td className="num font-semibold text-slate-900">{pct(a.compliance_percent)}</td>
                  <td className="text-slate-500">{formatDate(a.finished_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(data || []).length === 0 && (
          <p className="p-4 text-sm text-slate-500">No audits yet. Upload a configuration and run an audit.</p>
        )}
      </div>
    </div>
  );
}

export function AuditDetail() {
  const { id } = useParams();
  const audit = useFetch(() => api.audit(id), [id]);
  const results = useFetch(() => api.results(id), [id]);
  const rules = useFetch(api.rules);
  const [explanations, setExplanations] = useState({});
  const [explaining, setExplaining] = useState(null);

  async function explainRow(r) {
    setExplaining(r.id);
    try {
      const out = await api.aiExplain({
        rule_code: r.rule_code,
        title: r.title,
        status: r.status,
        evidence: r.evidence,
        remediation: r.remediation,
      });
      setExplanations((m) => ({ ...m, [r.id]: out.explanation }));
    } catch (e) {
      setExplanations((m) => ({ ...m, [r.id]: `Explanation unavailable: ${e.message}` }));
    } finally {
      setExplaining(null);
    }
  }

  if (audit.loading || results.loading) return <LoadingState text="Loading audit…" />;
  if (audit.error) return <ErrorState message={audit.error} onRetry={audit.reload} />;
  if (results.error) return <ErrorState message={results.error} onRetry={results.reload} />;
  const rows = results.data || [];
  const failed = rows.filter((r) => r.status === "FAIL").length;
  const catByCode = Object.fromEntries(((rules.data || []).map((r) => [r.rule_code, r.category])));

  return (
    <div className="space-y-4">
      <Link to="/audits" className="text-xs font-semibold text-blue-800 hover:underline">
        ← Back to audits
      </Link>
      <PageHeader
        title={`Audit #${audit.data.id}`}
        description={`${pct(audit.data.compliance_percent)} compliant · ${rows.length - failed} passed · ${failed} failed · Finished ${formatDate(audit.data.finished_at)}`}
      />
      {rows.length === 0 ? (
        <EmptyState text="No rule results recorded for this audit." />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Severity</th>
                  <th>Evidence</th>
                  <th>Remediation</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <div className="mono text-slate-500">{r.rule_code}</div>
                      <div className="font-medium text-slate-900">{r.title}</div>
                      {explanations[r.id] && (
                        <div className="mt-2 text-xs text-blue-900 bg-blue-50 border border-blue-100 rounded-md p-2">
                          {explanations[r.id]}
                        </div>
                      )}
                    </td>
                    <td className="text-xs text-slate-500">{catByCode[r.rule_code] || "—"}</td>
                    <td>
                      <Badge value={r.status} />
                    </td>
                    <td>
                      <Badge value={r.severity} />
                    </td>
                    <td className="mono text-slate-600 max-w-xs">{r.evidence}</td>
                    <td className="max-w-xs text-slate-600">{r.remediation}</td>
                    <td>
                      <button
                        onClick={() => explainRow(r)}
                        disabled={explaining === r.id}
                        className="btn btn-sm btn-secondary"
                      >
                        {explaining === r.id ? "Working…" : "Explain"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
