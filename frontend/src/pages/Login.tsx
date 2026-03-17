import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { loginUser } from "../api/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    
    try {
      const token = await loginUser({ email, password });
      localStorage.setItem("auth_token", token);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Erro ao fazer login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-layout">
        <div className="auth-hero-panel">
          <div className="auth-hero-logo">
            <div className="auth-hero-logo-mark">H</div>
            <div className="auth-hero-logo-text">
              <span className="auth-hero-title">Hotel Automation</span>
              <span className="auth-hero-subtitle-small">SaaS para gestão de reservas e WhatsApp</span>
            </div>
          </div>

          <div className="auth-hero-copy">
            <span className="auth-badge">Painel multi-tenant</span>
            <h2>
              Centralize leads, reservas e check-ins{" "}
              <span className="auth-hero-highlight">em um só lugar</span>
            </h2>
            <p>
              Este login dá acesso ao painel SaaS do projeto. Após autenticar, você poderá explorar KPIs,
              funil de jornada e integrações com WhatsApp para diferentes hotéis.
            </p>
          </div>

          <ul className="auth-hero-list">
            <li>📊 KPIs em tempo real por hotel.</li>
            <li>🤖 Jornada automatizada via WhatsApp do primeiro contato ao checkout.</li>
            <li>🏨 Multi-tenant: uma conta, múltiplos hotéis isolados.</li>
          </ul>

          <div className="auth-hero-link">
            <span>Quer saber mais sobre o projeto?</span>
            <Link to="/" className="auth-link">
              Ver página de apresentação
            </Link>
          </div>
        </div>

        <div className="auth-container">
          <div className="auth-header">
            <h1 className="auth-title">Entrar no painel</h1>
            <p className="auth-subtitle">Use suas credenciais para acessar o SaaS</p>
          </div>

          <form onSubmit={handleLogin} className="auth-form">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Senha</label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <button type="submit" className="auth-button" disabled={isLoading}>
              {isLoading ? "Entrando..." : "Entrar"}
            </button>

            {error && <div className="error-message">{error}</div>}
          </form>

          <div className="auth-footer">
            <p>
              Não tem uma conta?{" "}
              <Link to="/register" className="auth-link">
                Registre-se
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
