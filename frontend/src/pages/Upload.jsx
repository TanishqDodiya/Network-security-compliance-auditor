// Upload a device configuration, review detection, then run an audit.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Badge from "../components/Badge.jsx";
import { Alert, Card, PageHeader } from "../components/ui.jsx";
import { api } from "../services/api.js";
import { formatBytes, formatDate } from "../utils/format.js";

export default function Upload() {
  const [file, setFile] = useState(null);
  const [deviceName, setDeviceName] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleUpload(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    if (!file) {
      setError("Choose a .txt, .conf or .cfg file first.");
      return;
    }
    setBusy(true);
    try {
      const out = await api.upload(file, deviceName.trim() || undefined);
      setResult(out);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAudit() {
    if (!result) return;
    setBusy(true);
    try {
      const run = await api.runAudit(result.configuration_id);
      navigate(`/audits/${run.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <PageHeader
        title="Upload configuration"
        description="Upload a network device configuration to begin the audit. Files are validated and stored as text — never executed."
      />

      <Card>
        <form onSubmit={handleUpload} aria-label="Upload configuration">
          <div className="mb-4">
            <label htmlFor="config-file" className="label">Configuration file</label>
            <input
              id="config-file"
              type="file"
              accept=".txt,.conf,.cfg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="input"
            />
            <p className="help">Supported formats: .txt, .conf, .cfg · Maximum size 2 MB</p>
          </div>
          <div className="mb-4">
            <label htmlFor="device-name" className="label">
              Device name <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input
              id="device-name"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              placeholder="Defaults to the file name"
              className="input"
            />
          </div>
          <button type="submit" disabled={busy} className="btn btn-primary">
            {busy && <span className="spinner" aria-hidden="true" />}
            {busy ? "Uploading…" : "Upload configuration"}
          </button>
        </form>
      </Card>

      {error && <Alert kind="error">{error}</Alert>}

      {result && (
        <Card>
          <h2 className="card-title mb-3">Detection result</h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <dt className="text-slate-500">File</dt>
            <dd className="font-medium text-slate-900 break-all">{result.filename}</dd>
            <dt className="text-slate-500">Detected vendor</dt>
            <dd><Badge value={result.detected_vendor} /></dd>
            <dt className="text-slate-500">Size</dt>
            <dd className="tabular-nums">{formatBytes(result.file_size)} · {result.line_count} lines</dd>
            <dt className="text-slate-500">Uploaded</dt>
            <dd>{formatDate(result.upload_time)}</dd>
            <dt className="text-slate-500">Status</dt>
            <dd><Badge value={result.status} /></dd>
          </dl>
          <div className="mt-4 pt-4 border-t border-slate-200">
            <button onClick={handleAudit} disabled={busy} className="btn btn-primary">
              {busy ? "Starting audit…" : "Run audit"}
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
