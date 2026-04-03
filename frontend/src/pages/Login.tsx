import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import api from '../utils/api';

export default function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('admin@carbonverify.com');
  const [password, setPassword] = useState('admin123');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      if (isRegister) {
        const { data } = await api.post('/auth/register', { email, password, full_name: fullName, organization_name: orgName });
        login(data.access_token, data.user);
      } else {
        const { data } = await api.post('/auth/login', { email, password });
        login(data.access_token, data.user);
      }
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao autenticar');
    } finally { setLoading(false); }
  };

  return (
    <div className="login-page">
      <div className="login-card fade-in">
        <div className="login-logo">
          <div className="icon">CV</div>
          <h2>Carbon Verify</h2>
          <p style={{ color: 'var(--cv-text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Plataforma de Verificação de Créditos de Carbono
          </p>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          {isRegister && (
            <>
              <div><label>Nome completo</label><input value={fullName} onChange={e => setFullName(e.target.value)} required /></div>
              <div><label>Organização</label><input value={orgName} onChange={e => setOrgName(e.target.value)} required /></div>
            </>
          )}
          <div><label>Email</label><input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></div>
          <div><label>Senha</label><input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></div>
          {error && <div style={{ color: 'var(--cv-danger)', fontSize: '0.85rem', textAlign: 'center' }}>{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Carregando...' : isRegister ? 'Criar Conta' : 'Entrar'}
          </button>
          <div style={{ textAlign: 'center' }}>
            <button type="button" onClick={() => setIsRegister(!isRegister)} style={{ background: 'none', border: 'none', color: 'var(--cv-primary)', cursor: 'pointer', fontSize: '0.85rem' }}>
              {isRegister ? 'Já tem conta? Fazer login' : 'Criar nova conta'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
