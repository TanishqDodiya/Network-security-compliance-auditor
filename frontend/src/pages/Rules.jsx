// Compliance rule catalog (authoritative demo rule definitions).
import Badge from "../components/Badge.jsx";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api } from "../services/api.js";

export default function Rules() {
  const { data, loading, error, reload } = useFetch(api.rules);
  if (loading) return <LoadingState text="Loading rules…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <div className="space-y-4">
      <PageHeader
        title="Compliance rules"
        description="Internally created demo rules evaluated against every audit. Not official CIS, NIST, or STIG controls."
      />
      {(data || []).length === 0 ? (
        <EmptyState text="No rules found. Run python seed_rules.py in backend/." />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Category</th>
                  <th>Severity</th>
                  <th>Check</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {(data || []).map((r) => (
                  <tr key={r.rule_code}>
                    <td>
                      <div className="mono text-slate-500">{r.rule_code}</div>
                      <div className="font-medium text-slate-900">{r.title}</div>
                      <div className="text-xs text-slate-500">{(r.framework || []).join(", ")}</div>
                    </td>
                    <td className="text-xs">{r.category}</td>
                    <td>
                      <Badge value={r.severity} />
                    </td>
                    <td className="mono text-slate-600">
                      {r.field} = {JSON.stringify(r.expected)}
                    </td>
                    <td className="max-w-sm text-slate-600">
                      {r.description}
                      {r.remediation && (
                        <div className="mt-1 text-xs">
                          <span className="font-semibold text-slate-700">Fix: </span>
                          {r.remediation}
                        </div>
                      )}
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
