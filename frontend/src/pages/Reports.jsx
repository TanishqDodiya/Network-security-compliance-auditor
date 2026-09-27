// Audit reports: per-audit PDF downloads.
import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api, apiUrl } from "../services/api.js";
import { formatDate, pct } from "../utils/format.js";

export default function Reports() {
  const { data, loading, error, reload } = useFetch(() => api.audits(100));
  const devices = useFetch(api.devices);
  const [downloading, setDownloading] = useState(null);
  const [msg, setMsg] = useState("");

  async function downloadPdf(auditId) {
    setDownloading(auditId);
    setMsg("");
    try {
      const res = await fetch(apiUrl(`/api/reports/${auditId}`));
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Download failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-${auditId}-compliance-report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setDownloading(null);
    }
  }

  if (loading) return <LoadingState text="Loading reports…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const nameById = Object.fromEntries(((devices.data || []).map((d) => [d.id, d.name])));

  return (
    <div className="space-y-4">
      <PageHeader
        title="Reports"
        description="Each audit run produces a PDF report with findings, evidence, and remediation."
      />
      {msg && <Alert kind="error">{msg}</Alert>}
      {(data || []).length === 0 ? (
        <EmptyState text="No audit reports yet. Run an audit to generate your first report." />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Device</th>
                  <th className="num">Compliance</th>
                  <th>Finished</th>
                  <th><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {(data || []).map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link to={`/audits/${a.id}`} className="font-semibold text-blue-800 hover:underline">
                        Audit #{a.id} report
                      </Link>
                    </td>
                    <td>{nameById[a.device_id] || `Device #${a.device_id}`}</td>
                    <td className="num font-semibold text-slate-900">{pct(a.compliance_percent)}</td>
                    <td className="text-slate-500">{formatDate(a.finished_at)}</td>
                    <td>
                      <button
                        onClick={() => downloadPdf(a.id)}
                        disabled={downloading === a.id}
                        className="btn btn-sm btn-secondary"
                      >
                        {downloading === a.id ? "Preparing…" : "Download PDF"}
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
