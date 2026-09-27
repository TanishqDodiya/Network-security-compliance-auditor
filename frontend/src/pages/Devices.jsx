// Devices registry + per-device configurations and audit history.
import { Link, useParams } from "react-router-dom";
import Badge from "../components/Badge.jsx";
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, SectionTitle, UploadLink } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api } from "../services/api.js";
import { formatDate, pct } from "../utils/format.js";

export function Devices() {
  const { data, loading, error, reload } = useFetch(api.devices);
  if (loading) return <LoadingState text="Loading devices…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return (
    <div className="space-y-4">
      <PageHeader
        title="Devices"
        description="Registered network devices and their detected vendors."
        action={<UploadLink />}
      />
      <div className="card">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Device</th>
                <th>Vendor</th>
                <th>Registered</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/devices/${d.id}`} className="font-semibold text-blue-800 hover:underline">
                      {d.name}
                    </Link>
                  </td>
                  <td>
                    <Badge value={d.vendor} />
                  </td>
                  <td className="text-slate-500">{formatDate(d.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(data || []).length === 0 && (
          <p className="p-4 text-sm text-slate-500">No devices yet. Upload a configuration first.</p>
        )}
      </div>
    </div>
  );
}

export function DeviceDetail() {
  const { id } = useParams();
  const device = useFetch(() => api.device(id), [id]);
  const configs = useFetch(api.configurations);
  const audits = useFetch(() => api.audits(100));

  if (device.loading) return <LoadingState text="Loading device…" />;
  if (device.error) return <ErrorState message={device.error} onRetry={device.reload} />;
  const d = device.data;
  const myConfigs = (configs.data || []).filter((c) => c.device_id === Number(id));
  const myAudits = (audits.data || []).filter((a) => a.device_id === Number(id));
  const latest = myAudits[0];

  return (
    <div className="space-y-4">
      <Link to="/devices" className="text-xs font-semibold text-blue-800 hover:underline">
        ← Back to devices
      </Link>
      <PageHeader
        title={d.name}
        description={`Vendor: ${d.vendor} · Registered ${formatDate(d.created_at)}`}
      />
      {latest && (
        <Card>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">Latest compliance</span>
            <span className="text-xl font-bold text-slate-900 tabular-nums">
              {pct(latest.compliance_percent)}
            </span>
            <Link to={`/audits/${latest.id}`} className="btn btn-sm btn-secondary">
              Open audit #{latest.id}
            </Link>
          </div>
        </Card>
      )}
      <Card>
        <SectionTitle>Configurations ({myConfigs.length})</SectionTitle>
        {myConfigs.length === 0 ? (
          <EmptyState text="No configurations recorded for this device." />
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {myConfigs.map((c) => (
                  <tr key={c.id}>
                    <td className="mono">{c.filename}</td>
                    <td><Badge value={c.status} /></td>
                    <td className="text-slate-500">{formatDate(c.upload_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Card>
        <SectionTitle>Audit history ({myAudits.length})</SectionTitle>
        {myAudits.length === 0 ? (
          <EmptyState text="No audits yet for this device." />
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Audit</th>
                  <th className="num">Compliance</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {myAudits.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link to={`/audits/${a.id}`} className="font-semibold text-blue-800 hover:underline">
                        Audit #{a.id}
                      </Link>
                    </td>
                    <td className="num font-semibold text-slate-900">{pct(a.compliance_percent)}</td>
                    <td className="text-slate-500">{formatDate(a.finished_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
