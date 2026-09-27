import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { AuditDetail, Audits } from "./pages/Audits.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { DeviceDetail, Devices } from "./pages/Devices.jsx";
import Mappings from "./pages/Mappings.jsx";
import Reports from "./pages/Reports.jsx";
import Rules from "./pages/Rules.jsx";
import Settings from "./pages/Settings.jsx";
import Upload from "./pages/Upload.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/devices/:id" element={<DeviceDetail />} />
          <Route path="/audits" element={<Audits />} />
          <Route path="/audits/:id" element={<AuditDetail />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/unknown-mappings" element={<Mappings />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
