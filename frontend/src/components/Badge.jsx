// One consistent badge system. Color = meaning only (status/severity).
const CLASS_BY_VALUE = {
  PASS: "badge-pass",
  FAIL: "badge-fail",
  CRITICAL: "badge-critical",
  HIGH: "badge-high",
  MEDIUM: "badge-medium",
  LOW: "badge-low",
  PENDING: "badge-medium",
  CONFIRMED: "badge-pass",
  REJECTED: "badge-fail",
  READY: "badge-info",
  COMPLETED: "badge-pass",
  RUNNING: "badge-info",
};

const VENDOR_CLASS = {
  cisco: "badge-info",
  juniper: "badge-neutral",
  paloalto: "badge-low",
  unknown: "badge-neutral",
};

export default function Badge({ value, tone }) {
  const raw = String(value ?? "");
  const upper = raw.toUpperCase();
  let cls = tone || CLASS_BY_VALUE[upper] || VENDOR_CLASS[raw.toLowerCase()];
  if (!cls) {
    // Prefix matches for compound states like "Ready for Audit".
    if (upper.startsWith("READY")) cls = "badge-info";
    else if (upper.startsWith("AUDIT")) cls = "badge-pass";
    else cls = "badge-neutral";
  }
  return <span className={`badge ${cls}`}>{raw}</span>;
}
