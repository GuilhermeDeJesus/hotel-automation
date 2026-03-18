import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <div className="landing-logo">
          <span className="landing-logo-mark">H</span>
          <div className="landing-logo-text">
            <span className="landing-logo-title">Hotel Automation</span>
            <span className="landing-logo-subtitle">Funil de reservas e automação via WhatsApp</span>
          </div>
        </div>

        <nav className="landing-nav">
          <Link to="/login" className="landing-nav-link">
            <span className="landing-cta-text">Entrar no SaaS</span>
            <span className="landing-cta-icon" aria-hidden="true">
              →
            </span>
          </Link>
        </nav>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-hero-content">
            <h1>
              Transforme conversas em reservas
              <span className="landing-hero-highlight"> em poucos cliques</span>
            </h1>
            <p className="landing-hero-subtitle">
              O painel que conecta WhatsApp, pagamentos e gestão de reservas em um só lugar, pensado para hotéis,
              pousadas e suítes com operação enxuta.
            </p>

            <div className="landing-hero-actions">
              <Link to="/login" className="landing-cta-primary">
              <span className="landing-cta-text">Entrar no SaaS</span>
              <span className="landing-cta-icon" aria-hidden="true">
                →
              </span>
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="landing-cta-secondary"
              >
                Ver código do projeto
              </a>
            </div>

            <ul className="landing-bullets">
              <li>🧾 Acompanhe o funil completo: leads, reservas, check-in e pagamentos.</li>
              <li>🤖 Fluxo de atendimento via WhatsApp integrado ao backend do projeto.</li>
              <li>📊 KPIs em tempo real para entender desempenho por canal e período.</li>
            </ul>
          </div>

          <div className="landing-hero-card">
            <div className="landing-card-header">
              <span className="landing-card-badge">Visão geral do painel</span>
              <h2>Dashboard de reservas</h2>
              <p>Acompanhe diariamente como suas conversas viram hóspedes na recepção.</p>
            </div>

            <div className="landing-card-grid">
              <div className="landing-metric">
                <div className="landing-metric-label">Leads captados (7 dias)</div>
                <div className="landing-metric-value">+128</div>
                <div className="landing-metric-trend positive">+18% vs. período anterior</div>
              </div>
              <div className="landing-metric">
                <div className="landing-metric-label">Taxa de confirmação</div>
                <div className="landing-metric-value">42%</div>
                <div className="landing-metric-trend positive">+6 p.p.</div>
              </div>
              <div className="landing-metric">
                <div className="landing-metric-label">Tempo médio de resposta</div>
                <div className="landing-metric-value">27s</div>
                <div className="landing-metric-trend neutral">automatizado pela IA</div>
              </div>
              <div className="landing-metric">
                <div className="landing-metric-label">Check-ins via WhatsApp</div>
                <div className="landing-metric-value">63</div>
                <div className="landing-metric-trend positive">menos fila na recepção</div>
              </div>
            </div>

            <div className="landing-card-footer">
              <p>
                Depois de logar, você acessa este painel completo, com filtros por período, origem de lead e hotel
                (multi-tenant).
              </p>
            </div>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-section-content">
            <h2>O que este projeto demonstra</h2>
            <div className="landing-section-grid">
              <div className="landing-section-item">
                <h3>Arquitetura limpa</h3>
                <p>
                  Backend organizado em camadas (domain, application, infrastructure, interfaces) para manter regras de
                  negócio desacopladas de frameworks.
                </p>
              </div>
              <div className="landing-section-item">
                <h3>Multi-tenant SaaS</h3>
                <p>
                  Uma mesma instalação atendendo múltiplos hotéis, com isolamento por `hotelId` e dashboards dedicados
                  por tenant.
                </p>
              </div>
              <div className="landing-section-item">
                <h3>Automação de jornada</h3>
                <p>
                  Do primeiro contato até o checkout: funil de leads, confirmação de reserva, check-in via WhatsApp e
                  acompanhamento de pagamentos.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section landing-section-muted">
          <div className="landing-section-content landing-section-cta">
            <div>
              <h2>Pronto para explorar o painel?</h2>
              <p>
                Use o botão abaixo para entrar no SaaS, criar um hotel de teste (se aplicável) e navegar pelos
                dashboards em tempo real.
              </p>
            </div>
            <Link to="/login" className="landing-cta-primary">
              <span className="landing-cta-text">Entrar no SaaS</span>
              <span className="landing-cta-icon" aria-hidden="true">
                →
              </span>
            </Link>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>Hotel Automation — projeto de automação para hotéis e pousadas.</span>
        <span className="landing-footer-separator">•</span>
        <span>
          Frontend em React + Vite, backend em FastAPI / SQLAlchemy, multi-tenant e WhatsApp integrado.
        </span>
      </footer>
    </div>
  );
}

