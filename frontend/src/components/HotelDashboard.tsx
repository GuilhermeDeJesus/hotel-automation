import { useState } from "react";
import { useDashboardStats, useRevenueAnalytics, formatCurrency, formatPercentage, getOccupancyColor } from "../api/dashboard";
import { useHotelConfig } from "../api/hotelConfig";

interface HotelDashboardProps {
  hotelId: string;
}

export default function HotelDashboard({ hotelId }: HotelDashboardProps) {
  const { stats, loading: statsLoading, error: statsError } = useDashboardStats(hotelId);
  const { analytics, loading: analyticsLoading } = useRevenueAnalytics(hotelId);
  const { config, loading: configLoading } = useHotelConfig(hotelId);

  const [selectedPeriod, setSelectedPeriod] = useState(30);

  if (statsLoading || analyticsLoading || configLoading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Carregando dashboard...</p>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="dashboard-error">
        <p>Erro ao carregar dashboard: {statsError}</p>
      </div>
    );
  }

  if (!stats || !config) {
    return (
      <div className="dashboard-empty">
        <p>Nenhum dado disponível</p>
      </div>
    );
  }

  return (
    <div className="hotel-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="hotel-info">
          <h1>{stats.hotel_name}</h1>
          <p>Dashboard dos últimos {selectedPeriod} dias</p>
        </div>
        <div className="period-selector">
          <select 
            value={selectedPeriod} 
            onChange={(e) => setSelectedPeriod(Number(e.target.value))}
            className="period-select"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
          </select>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon revenue-icon">
            <span>💰</span>
          </div>
          <div className="metric-content">
            <h3>Receita Total</h3>
            <p className="metric-value">{formatCurrency(stats.total_revenue, config.currency)}</p>
            <span className="metric-period">Período de {selectedPeriod} dias</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon occupancy-icon">
            <span>🏨</span>
          </div>
          <div className="metric-content">
            <h3>Taxa de Ocupação</h3>
            <p className="metric-value" style={{ color: getOccupancyColor(stats.occupancy_rate) }}>
              {formatPercentage(stats.occupancy_rate)}
            </p>
            <span className="metric-period">{stats.occupied_rooms} de {stats.total_rooms} quartos</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon reservations-icon">
            <span>📋</span>
          </div>
          <div className="metric-content">
            <h3>Reservas</h3>
            <p className="metric-value">{stats.total_reservations}</p>
            <div className="reservations-breakdown">
              <span className="confirmed">{stats.confirmed_reservations} confirmadas</span>
              <span className="pending">{stats.pending_reservations} pendentes</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon customers-icon">
            <span>👥</span>
          </div>
          <div className="metric-content">
            <h3>Clientes</h3>
            <p className="metric-value">{stats.total_customers}</p>
            <span className="metric-period">+{stats.new_customers_this_period} novos no período</span>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="charts-section">
        <div className="chart-container">
          <h3>Receita Diária</h3>
          {analytics?.daily_revenue && analytics.daily_revenue.length > 0 ? (
            <div className="revenue-chart">
              {analytics.daily_revenue.map((day, index) => (
                <div key={index} className="chart-bar">
                  <div 
                    className="bar" 
                    style={{ 
                      height: `${(day.revenue / Math.max(...analytics.daily_revenue.map(d => d.revenue))) * 100}%` 
                    }}
                  ></div>
                  <span className="bar-label">{new Date(day.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}</span>
                  <span className="bar-value">{formatCurrency(day.revenue, config.currency)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">Sem dados de receita disponíveis</p>
          )}
        </div>

        <div className="chart-container">
          <h3>Distribuição por Tipo de Quarto</h3>
          {analytics?.revenue_by_room_type ? (
            <div className="room-type-chart">
              {Object.entries(analytics.revenue_by_room_type).map(([type, revenue]) => (
                <div key={type} className="room-type-item">
                  <div className="room-type-info">
                    <span className="room-type">{type}</span>
                    <span className="revenue">{formatCurrency(revenue, config.currency)}</span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ 
                        width: `${(revenue / Math.max(...Object.values(analytics.revenue_by_room_type))) * 100}%` 
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">Sem dados de distribuição disponíveis</p>
          )}
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="additional-metrics">
        <div className="metric-group">
          <h3>Pagamentos</h3>
          <div className="metric-row">
            <span>Total:</span>
            <span>{stats.total_payments}</span>
          </div>
          <div className="metric-row">
            <span className="success">Sucesso:</span>
            <span className="success">{stats.successful_payments}</span>
          </div>
          <div className="metric-row">
            <span className="error">Falha:</span>
            <span className="error">{stats.failed_payments}</span>
          </div>
          <div className="metric-row">
            <span>Taxa de sucesso:</span>
            <span>{formatPercentage((stats.successful_payments / stats.total_payments) * 100)}</span>
          </div>
        </div>

        <div className="metric-group">
          <h3>Quartos</h3>
          <div className="metric-row">
            <span>Total:</span>
            <span>{stats.total_rooms}</span>
          </div>
          <div className="metric-row">
            <span className="occupied">Ocupados:</span>
            <span className="occupied">{stats.occupied_rooms}</span>
          </div>
          <div className="metric-row">
            <span className="available">Disponíveis:</span>
            <span className="available">{stats.available_rooms}</span>
          </div>
          <div className="metric-row">
            <span className="maintenance">Manutenção:</span>
            <span className="maintenance">{stats.maintenance_rooms}</span>
          </div>
        </div>

        <div className="metric-group">
          <h3>Suporte</h3>
          <div className="metric-row">
            <span>Total:</span>
            <span>{stats.total_support_tickets}</span>
          </div>
          <div className="metric-row">
            <span className="open">Abertos:</span>
            <span className="open">{stats.open_tickets}</span>
          </div>
          <div className="metric-row">
            <span className="resolved">Resolvidos:</span>
            <span className="resolved">{stats.resolved_tickets}</span>
          </div>
          <div className="metric-row">
            <span>Tempo médio:</span>
            <span>{stats.average_resolution_time_hours}h</span>
          </div>
        </div>

        <div className="metric-group">
          <h3>Pedidos de Quarto</h3>
          <div className="metric-row">
            <span>Total:</span>
            <span>{stats.room_orders_count}</span>
          </div>
          <div className="metric-row">
            <span className="pending">Pendentes:</span>
            <span className="pending">{stats.pending_orders}</span>
          </div>
          <div className="metric-row">
            <span className="completed">Concluídos:</span>
            <span className="completed">{stats.completed_orders}</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h3>Ações Rápidas</h3>
        <div className="actions-grid">
          <button className="action-button">
            <span>📊</span>
            <span>Ver Relatório Completo</span>
          </button>
          <button className="action-button">
            <span>📧</span>
            <span>Enviar Newsletter</span>
          </button>
          <button className="action-button">
            <span>⚙️</span>
            <span>Configurar Hotel</span>
          </button>
          <button className="action-button">
            <span>📱</span>
            <span>Configurar WhatsApp</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// CSS styles (you can move this to a separate CSS file)
