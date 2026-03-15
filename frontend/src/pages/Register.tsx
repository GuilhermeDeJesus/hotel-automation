import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { registerUser } from "../api/auth";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [hotelId, setHotelId] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    
    try {
      await registerUser({ email, password, hotel_id: hotelId || undefined });
      navigate("/login");
    } catch (err: any) {
      setError(err.message || "Erro ao registrar usuário");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <h1 className="auth-title">Hotel Automation</h1>
          <p className="auth-subtitle">Crie sua conta para acessar o sistema</p>
        </div>
        
        <form onSubmit={handleRegister} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
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
              onChange={e => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="hotelId">Hotel ID (opcional)</label>
            <input
              id="hotelId"
              type="text"
              placeholder="ID do seu hotel"
              value={hotelId}
              onChange={e => setHotelId(e.target.value)}
              disabled={isLoading}
            />
            <small>Deixe em branco se você não tem um hotel associado</small>
          </div>
          
          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? "Registrando..." : "Registrar"}
          </button>
          
          {error && <div className="error-message">{error}</div>}
        </form>
        
        <div className="auth-footer">
          <p>
            Já tem uma conta? <Link to="/login" className="auth-link">Faça login</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
