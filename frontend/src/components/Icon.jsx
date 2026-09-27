// Consistent 16px stroke icons (single style, purpose-driven only).
const paths = {
  dashboard: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  upload: "M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3",
  devices: "M4 17V7l8-4 8 4v10M4 17h16M4 17l3-6m12 6l-3-6M12 11v6",
  audits: "M9 12l2 2 4-4m-6 8h8a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2h2",
  rules: "M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6z",
  mappings: "M8 7h13m-13 6h13M3 7h.01M3 13h.01M3 19h13M17 16l4 4m0-4l-4 4",
  reports: "M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zm7 0v5h5M9 13h6M9 17h6",
  settings: "M4 8h10m4 0h2M4 16h4m4 0h8M14 4v4m0 8v4",
};

export default function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[name] || paths.dashboard} />
    </svg>
  );
}
