import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  IconOverview,
  IconLeads,
  IconFunnel,
  IconChart,
  IconCalendar,
  IconCreditCard,
  IconSettings,
  IconAudit,
  IconRefresh,
  IconMenu,
  IconSun,
  IconMoon,
  IconMessage,
} from "./Icons";
import { getAdminToken, invalidateCache, fetchHotelsList } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { useTheme } from "../contexts/ThemeContext";
import { useTenant } from "../contexts/TenantContext";
import { useHotelConfig } from "../api/hotelConfig";
import { logoutUser } from "../api/authUtils";

interface LayoutProps {
  children: React.ReactNode;
}

const MOBILE_BREAKPOINT = 768;

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [cacheLoading, setCacheLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const { showToast } = useToast();
  const { theme, toggleTheme } = useTheme();
  const { hotelId, role, setHotelId } = useTenant();
  const { config: hotelConfig } = useHotelConfig(hotelId);
  const [hotels, setHotels] = useState<{ id: string; name: string }[]>([]);
  const [loadingHotels, setLoadingHotels] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    if (!isMobile) setSidebarOpen(false);
  }, [isMobile, location.pathname]);

  // Carrega lista de hotéis para super admin (role=admin e sem hotelId no token)
  useEffect(() => {
    const isSuperAdmin = role === "admin";
    if (!isSuperAdmin) return;
    if (hotels.length > 0) return;
    setLoadingHotels(true);
    fetchHotelsList()
      .then((items) => setHotels(items))
      .catch((e) => {
        console.error("Erro ao carregar hotéis:", e);
      })
      .finally(() => setLoadingHotels(false));
  }, [role, hotels.length]);

  const handleInvalidateCache = async () => {
    if (!getAdminToken()) {
      showToast("Token admin não configurado. Acesse Auditoria.", "error");
      return;
    }
    setCacheLoading(true);
    try {
      const res = await invalidateCache();
      showToast(`Cache invalidado (${res.deleted_keys} chaves). Recarregando...`, "success");
      setTimeout(() => window.location.reload(), 800);
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Erro ao invalidar cache", "error");
    } finally {
      setCacheLoading(false);
    }
  };

  const navItems = [
    { path: "/dashboard", label: "Overview", icon: IconOverview },
    { path: "/leads", label: "Leads", icon: IconLeads },
    { path: "/funnel", label: "Funil de conversão", icon: IconFunnel },
    { path: "/timeseries", label: "Evolução temporal", icon: IconChart },
    { path: "/reservations", label: "Reservas", icon: IconCalendar },
    { path: "/payments", label: "Pagamentos", icon: IconCreditCard },
    { path: "/hotel-config", label: "Config. hotel", icon: IconSettings },
    { path: "/whatsapp-config", label: "WhatsApp (IA)", icon: IconMessage },
    { path: "/admin/audit", label: "Auditoria", icon: IconAudit },
  ];

  return (
    <div style={{ minHeight: "100vh", display: "flex" }}>
      {/* Sidebar overlay (mobile) */}
      {isMobile && sidebarOpen && (
        <div
          role="button"
          tabIndex={0}
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => e.key === "Escape" && setSidebarOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            zIndex: 40,
          }}
          aria-label="Fechar menu"
        />
      )}
      {/* Sidebar */}
      <aside
        style={{
          width: "var(--sidebar-width)",
          minWidth: "var(--sidebar-width)",
          background: "var(--color-bg-elevated)",
          borderRight: "1px solid var(--color-border)",
          padding: "1.5rem 0",
          position: isMobile ? "fixed" : "sticky",
          top: 0,
          height: "100vh",
          zIndex: 50,
          transform: isMobile && !sidebarOpen ? "translateX(-100%)" : "translateX(0)",
          transition: "transform 0.2s ease",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ padding: "0 1.25rem", marginBottom: "2rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, var(--color-accent) 0%, #1d4ed8 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 700,
                fontSize: "1.1rem",
              }}
            >
              H
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: "1.1rem", letterSpacing: "-0.02em" }}>
                Hotel Automation
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                Painel de Leads
              </div>
            </div>
          </div>
        </div>
        <nav
          style={{
            flex: 1,
            overflowY: "auto",
            paddingBottom: "1rem",
          }}
        >
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem 1.25rem",
                  margin: "0 0.75rem",
                  borderRadius: "var(--radius-sm)",
                  color: isActive ? "var(--color-accent)" : "var(--color-text-muted)",
                  background: isActive ? "var(--color-accent-muted)" : "transparent",
                  fontWeight: isActive ? 600 : 500,
                  textDecoration: "none",
                  transition: "all 0.2s",
                  borderLeft: isActive ? "3px solid var(--color-accent)" : "3px solid transparent",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = "var(--color-surface-hover)";
                    e.currentTarget.style.color = "var(--color-text-secondary)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = "var(--color-text-muted)";
                  }
                }}
              >
                <Icon />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            background: "var(--color-bg-elevated)",
            borderBottom: "1px solid var(--color-border)",
            padding: "1rem 2rem",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              {isMobile && (
                <button
                  type="button"
                  onClick={() => setSidebarOpen(true)}
                  aria-label="Abrir menu"
                  style={{
                    padding: "0.5rem",
                    background: "transparent",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--color-text-muted)",
                    cursor: "pointer",
                  }}
                >
                  <IconMenu />
                </button>
              )}
              {role === "admin" && hotels.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                  <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>Selecionar hotel</div>
                  <select
                    value={hotelId || ""}
                    onChange={(e) => {
                      const value = e.target.value || null;
                      setHotelId(value);
                    }}
                    style={{
                      minWidth: 200,
                      padding: "0.25rem 0.5rem",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                      background: "var(--color-bg)",
                      color: "var(--color-text)",
                      fontSize: "0.875rem",
                    }}
                  >
                    <option value="">{loadingHotels ? "Carregando hotéis..." : "Escolha um hotel"}</option>
                    {hotels.map((h) => (
                      <option key={h.id} value={h.id}>
                        {h.name}
                      </option>
                    ))}
                  </select>
                  {hotelId && (
                    <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                      Hotel ID: {hotelId}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "0.9375rem", fontWeight: 600 }}>
                    {hotelConfig?.hotel_name ?? "Painel de gestão"}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>
                    {hotelId ? `Hotel ID: ${hotelId}` : "Bem-vindo ao painel de gestão"}
                  </div>
                </div>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button
                type="button"
                onClick={toggleTheme}
                aria-label={theme === "dark" ? "Modo claro" : "Modo escuro"}
                title={theme === "dark" ? "Modo claro" : "Modo escuro"}
                style={{
                  padding: "0.5rem",
                  background: "var(--color-bg-elevated)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-text-muted)",
                  cursor: "pointer",
                }}
              >
                {theme === "dark" ? <IconSun /> : <IconMoon />}
              </button>
              <button
                type="button"
                onClick={handleInvalidateCache}
                disabled={cacheLoading}
                title="Invalidar cache e recarregar dados"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.5rem 0.875rem",
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  color: "var(--color-accent)",
                  background: "var(--color-accent-muted)",
                  border: "1px solid var(--color-accent)",
                  borderRadius: "var(--radius-sm)",
                  cursor: cacheLoading ? "not-allowed" : "pointer",
                  opacity: cacheLoading ? 0.7 : 1,
                }}
              >
                <IconRefresh />
                {cacheLoading ? "Atualizando..." : "Atualizar dados"}
              </button>
              <button
                type="button"
                onClick={logoutUser}
                style={{
                  padding: "0.5rem 0.875rem",
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  color: "var(--color-error)",
                  background: "transparent",
                  border: "1px solid var(--color-error)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                }}
              >
                Sair
              </button>
            </div>
          </div>
        </header>
        <main style={{ flex: 1, padding: "2rem", overflow: "auto" }}>{children}</main>
      </div>
    </div>
  );
}
