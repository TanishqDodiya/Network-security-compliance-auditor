// Enterprise app shell: white sidebar, subtle active state, top bar.
import { NavLink, Outlet, useLocation } from "react-router-dom";
import Icon from "./Icon.jsx";

const links = [
  ["Dashboard", "/dashboard", "dashboard"],
  ["Upload", "/upload", "upload"],
  ["Devices", "/devices", "devices"],
  ["Audits", "/audits", "audits"],
  ["Rules", "/rules", "rules"],
  ["Unknown Mappings", "/unknown-mappings", "mappings"],
  ["Reports", "/reports", "reports"],
  ["Settings", "/settings", "settings"],
];

function NavItems({ mobile = false }) {
  return links.map(([label, to, icon]) => (
    <NavLink
      key={to}
      to={to}
      className={({ isActive }) =>
        mobile
          ? `px-3 py-1.5 rounded-md text-xs whitespace-nowrap transition-colors ${
              isActive ? "bg-blue-50 text-blue-800 font-semibold" : "text-slate-600"
            }`
          : `navlink ${isActive ? "navlink-active" : ""}`
      }
    >
      {!mobile && <Icon name={icon} />}
      {label}
    </NavLink>
  ));
}

export default function Layout() {
  const { pathname } = useLocation();
  return (
    <div className="min-h-screen flex text-slate-700">
      <aside className="w-60 shrink-0 bg-white border-r border-slate-200 hidden md:flex md:flex-col">
        <div className="px-4 pt-5 pb-4 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-8 h-8 rounded-md bg-blue-900 text-white text-sm font-bold">
              N
            </span>
            <div>
              <div className="text-sm font-bold text-slate-900 leading-tight">
                Compliance Auditor
              </div>
              <div className="text-xs text-slate-500">Network Security</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-0.5" aria-label="Primary">
          <NavItems />
        </nav>
        <div className="p-4 border-t border-slate-200 text-xs text-slate-500">
          Hackathon MVP · v0.2
        </div>
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="md:hidden bg-white border-b border-slate-200 px-3 py-2">
          <nav className="flex gap-1.5 overflow-x-auto" aria-label="Primary">
            <NavItems mobile />
          </nav>
        </header>
        <main className="flex-1 w-full max-w-6xl mx-auto p-4 md:p-6">
          <div className="page-enter" key={pathname}>
            <Outlet />
          </div>
        </main>
        <footer className="px-4 md:px-6 py-3 text-xs text-slate-400 border-t border-slate-200 bg-white">
          Configuration-level demo checks · Demo Security Rules · Not a full security assessment
        </footer>
      </div>
    </div>
  );
}
