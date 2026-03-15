import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Funnel from "./pages/Funnel";
import Timeseries from "./pages/Timeseries";
import Reservations from "./pages/Reservations";
import Payments from "./pages/Payments";
import HotelConfig from "./pages/HotelConfig";
import AdminAudit from "./pages/AdminAudit";
import Register from "./pages/Register";
import Login from "./pages/Login";
import { isAuthenticated } from "./api/authUtils";

function App() {
  const location = useLocation();
  const protectedRoute = (element: JSX.Element) =>
    isAuthenticated() ? element : <Navigate to="/login" state={{ from: location }} />;

  const isAuthPage = location.pathname === "/login" || location.pathname === "/register";

  return (
    <>
      {isAuthPage ? (
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      ) : (
        <Layout>
          <Routes>
            <Route path="/" element={protectedRoute(<Dashboard />)} />
            <Route path="/leads" element={protectedRoute(<Leads />)} />
            <Route path="/funnel" element={protectedRoute(<Funnel />)} />
            <Route path="/timeseries" element={protectedRoute(<Timeseries />)} />
            <Route path="/reservations" element={protectedRoute(<Reservations />)} />
            <Route path="/payments" element={protectedRoute(<Payments />)} />
            <Route path="/hotel-config" element={protectedRoute(<HotelConfig />)} />
            <Route path="/admin/audit" element={protectedRoute(<AdminAudit />)} />
          </Routes>
        </Layout>
      )}
    </>
  );
}

export default App;
