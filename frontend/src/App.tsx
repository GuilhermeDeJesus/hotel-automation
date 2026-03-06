import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Funnel from "./pages/Funnel";
import Timeseries from "./pages/Timeseries";
import Reservations from "./pages/Reservations";
import Payments from "./pages/Payments";
import HotelConfig from "./pages/HotelConfig";
import AdminAudit from "./pages/AdminAudit";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/leads" element={<Leads />} />
        <Route path="/funnel" element={<Funnel />} />
        <Route path="/timeseries" element={<Timeseries />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/hotel-config" element={<HotelConfig />} />
        <Route path="/admin/audit" element={<AdminAudit />} />
      </Routes>
    </Layout>
  );
}

export default App;
