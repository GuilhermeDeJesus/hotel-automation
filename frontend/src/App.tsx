import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Funnel from "./pages/Funnel";
import Timeseries from "./pages/Timeseries";
import Reservations from "./pages/Reservations";
import Payments from "./pages/Payments";
import HotelConfig from "./pages/HotelConfig";
import WhatsAppConfig from "./pages/WhatsAppConfig";
import AdminAudit from "./pages/AdminAudit";
import Register from "./pages/Register";
import Login from "./pages/Login";
import { isAuthenticated } from "./api/authUtils";
import Landing from "./pages/Landing";

function App() {
  const location = useLocation();
  const protectedRoute = (element: JSX.Element) =>
    isAuthenticated() ? element : <Navigate to="/login" state={{ from: location }} />;

  const isAuthPage = location.pathname === "/login" || location.pathname === "/register";
  const isLandingPage = location.pathname === "/";

  return (
    <>
      {isAuthPage ? (
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      ) : isLandingPage ? (
        <Routes>
          <Route
            path="/"
            element={isAuthenticated() ? <Navigate to="/dashboard" replace /> : <Landing />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      ) : (
        <Layout>
          <Routes>
            <Route path="/dashboard" element={protectedRoute(<Dashboard />)} />
            <Route path="/leads" element={protectedRoute(<Leads />)} />
            <Route path="/funnel" element={protectedRoute(<Funnel />)} />
            <Route path="/timeseries" element={protectedRoute(<Timeseries />)} />
            <Route path="/reservations" element={protectedRoute(<Reservations />)} />
            <Route path="/payments" element={protectedRoute(<Payments />)} />
            <Route path="/hotel-config" element={protectedRoute(<HotelConfig />)} />
            <Route path="/whatsapp-config" element={protectedRoute(<WhatsAppConfig />)} />
            <Route path="/hotel/config" element={<Navigate to="/hotel-config" replace />} />
            <Route path="/admin/audit" element={protectedRoute(<AdminAudit />)} />
          </Routes>
        </Layout>
      )}
    </>
  );
}

export default App;
