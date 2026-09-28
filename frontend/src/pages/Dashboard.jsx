// Dashboard: compliance overview — metrics, charts, recent audits.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import StatCard from "../components/StatCard.jsx";
import { BackendUnreachable, Card, EmptyState, LoadingState, PageHeader, UploadLink } from "../components/ui.jsx";
import { useFetch } from "../hooks/useFetch.js";
import { api } from "../services/api.js";
import { formatDate, pct } from "../utils/format.js";

const SEV_COLORS = { CRITICAL: "#991b1b", HIGH: "#c2410c", MEDIUM: "#b45309", LOW: "#64748b" };
const VND_COLORS = { cisco: "#1d4ed8", juniper: "#0f7667", paloalto: "#475569", unknown: "#94a3b8" };
const AXIS = "#64748b";
const GRID = "#e2e8f0";

export default function Dashboard() {
  const devices = useFetch(api.devices);
  const audits = useFetch(() => api.audits(100));
  const rules = useFetch(api.rules);
  const [resultsByAudit, setResultsByAudit] = useState({});

  // Load results for recent audits to build PASS/FAIL + severity charts.
  useEffect(() => {
    if (!audits.data) return;
    let cancelled = false;
    (async () => {
      const map = {};
      for (const run of audits.data.slice(0, 20)) {
        try {
          map[run.id] = await api.results(run.id);
        } catch {
          map[run.id] = [];
        }
        if (cancelled) break;
      }
      if (!cancelled) setResultsByAudit(map);
    })();
    return () => {
      cancelled = true;
    };
  }, [audits.data]);

  if (devices.loading || audits.loading) return <LoadingState text="Loading dashboard…" />;
  if (devices.error || audits.error)
    return <BackendUnreachable detail={devices.error || audits.error} onRetry={() => { devices.reload(); audits.reload(); }} />;

  const deviceList = devices.data || [];
  const auditList = audits.data || [];
  const allResults = Object.values(resultsByAudit).flat();
  const passed = allResults.filter((r) => r.status === "PASS").length;
  const failed = allResults.filter((r) => r.status === "FAIL").length;
  const sev = ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => ({
    name: s,
    value: allResults.filter((r) => r.status === "FAIL" && r.severity === s).length,
  }));
  const vendors = [...new Set(deviceList.map((d) => d.vendor))].map((v) => ({
    name: v,
    value: deviceList.filter((d) => d.vendor === v).length,
  }));
  const avgCompliance =
    auditList.length === 0
      ? 0
      : (auditList.reduce((s, a) => s + (a.compliance_percent || 0), 0) / auditList.length).toFixed(1);
  const compliant = auditList.filter((a) => (a.compliance_percent || 0) >= 80).length;

  // Category compliance from current results (real backend categories).
  const catByCode = Object.fromEntries(((rules.data || []).map((r) => [r.rule_code, r.category])));
  const cats = {};
  for (const r of allResults) {
    const key = catByCode[r.rule_code] || "Other";
    cats[key] = cats[key] || { name: key, pass: 0, total: 0 };
    cats[key].total += 1;
    if (r.status === "PASS") cats[key].pass += 1;
  }
  const catData = Object.values(cats).map((c) => ({
    name: c.name,
    compliance: c.total ? Math.round((c.pass / c.total) * 100) : 0,
  }));
  const recent = auditList.slice(0, 5);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Compliance overview"
        description="Device posture across vendors, recent audit results, and open findings."
        action={<UploadLink />}
      />

      <section aria-label="Key metrics">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard label="Devices" value={deviceList.length} sub={`${vendors.length} vendor(s)`} />
          <StatCard label="Audit runs" value={auditList.length} sub={`${new Set(auditList.map((a) => a.device_id)).size} device(s) audited`} />
          <StatCard label="Avg. compliance" value={`${avgCompliance}%`} sub={`PASS ${passed} · FAIL ${failed}`} />
          <StatCard label="Compliant (≥ 80%)" value={compliant} sub={`${auditList.length - compliant} non-compliant`} />
          <StatCard label="Critical findings" value={sev.find((s) => s.name === "CRITICAL")?.value || 0} sub="Needs immediate attention" />
          <StatCard label="High findings" value={sev.find((s) => s.name === "HIGH")?.value || 0} sub="Fix soon" />
          <StatCard label="Medium findings" value={sev.find((s) => s.name === "MEDIUM")?.value || 0} />
          <StatCard label="Rules evaluated" value={allResults.length} sub="Across recent audits" />
        </div>
      </section>

      {auditList.length === 0 ? (
        <EmptyState
          text="No audits yet. Upload a sample configuration to see compliance analytics."
          action={<UploadLink />}
        />
      ) : (
        <>
          <section aria-label="Analytics">
            <div className="grid md:grid-cols-2 gap-4">
              <ChartCard title="Findings by outcome" hint="Recent audits">
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={[{ name: "Pass", value: passed }, { name: "Fail", value: failed }]} dataKey="value" nameKey="name" outerRadius={80} label>
                      <Cell fill="#15803d" />
                      <Cell fill="#b91c1c" />
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Open findings by severity" hint="Failed checks only">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={sev} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                    <XAxis dataKey="name" stroke={AXIS} fontSize={12} tickLine={false} />
                    <YAxis stroke={AXIS} fontSize={12} allowDecimals={false} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {sev.map((s) => (
                        <Cell key={s.name} fill={SEV_COLORS[s.name]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Devices by vendor" hint="Registered devices">
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={vendors} dataKey="value" nameKey="name" outerRadius={80} label>
                      {vendors.map((v) => (
                        <Cell key={v.name} fill={VND_COLORS[v.name] || "#94a3b8"} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Compliance by category" hint="Percent passing">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={catData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                    <XAxis type="number" domain={[0, 100]} stroke={AXIS} fontSize={12} tickLine={false} />
                    <YAxis type="category" dataKey="name" stroke={AXIS} fontSize={11} width={130} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => [`${v}%`, "Compliance"]} />
                    <Bar dataKey="compliance" fill="#1e3a8a" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>
          </section>

          <section aria-label="Recent audits">
            <Card>
              <div className="flex items-center justify-between mb-2">
                <h2 className="card-title">Recent audits</h2>
                <Link to="/audits" className="text-xs font-semibold text-blue-800 hover:underline">
                  View all
                </Link>
              </div>
              <div className="table-wrap">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Audit</th>
                      <th>Compliance</th>
                      <th>Finished</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((a) => (
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
            </Card>
          </section>
        </>
      )}
    </div>
  );
}

function ChartCard({ title, hint, children }) {
  return (
    <Card>
      <div className="mb-1">
        <h2 className="card-title">{title}</h2>
        {hint && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
      {children}
    </Card>
  );
}
