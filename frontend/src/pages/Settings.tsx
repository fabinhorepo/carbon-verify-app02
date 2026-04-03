import { useEffect, useState } from 'react';

import api from '../utils/api';

export default function SettingsPage() {

  const [org, setOrg] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('org');

  useEffect(() => {
    api.get('/organizations/me').then(r => setOrg(r.data)).catch(() => {});
    api.get('/organizations/me/members').then(r => setMembers(r.data)).catch(() => {});
    api.get('/integrations/status').then(r => setIntegrations(r.data)).catch(() => {});
    api.get('/organizations/me/audit-log').then(r => setAuditLog(r.data)).catch(() => {});
  }, []);

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Configurações</h1></div>
      <div className="tabs">
        {[['org', 'Organização'], ['members', 'Membros'], ['integrations', 'Integrações'], ['audit', 'Log de Auditoria']].map(([k, v]) => (
          <div key={k} className={`tab ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{v}</div>
        ))}
      </div>

      {activeTab === 'org' && org && (
        <div className="card">
          <div className="grid-2">
            {[['Nome', org.name], ['Slug', org.slug], ['API Key', org.api_key ? `${org.api_key.slice(0, 20)}...` : 'Não gerada'], ['Plano', org.plan || 'Starter']].map(([k, v]) => (
              <div key={k as string} style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>{k}</div>
                <div style={{ fontWeight: 600, marginTop: '0.25rem' }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'members' && (
        <div className="card"><div className="table-wrap"><table><thead><tr><th>Nome</th><th>Email</th><th>Cargo</th><th>Status</th></tr></thead>
          <tbody>{members.map((m: any) => (
            <tr key={m.id}><td style={{ fontWeight: 600 }}>{m.full_name}</td><td>{m.email}</td>
              <td><span className="badge badge-blue">{m.role}</span></td>
              <td><span className={`badge ${m.is_active ? 'badge-green' : 'badge-red'}`}>{m.is_active ? 'Ativo' : 'Inativo'}</span></td></tr>
          ))}</tbody></table></div></div>
      )}

      {activeTab === 'integrations' && (
        <div className="card">{integrations.length > 0 ? (
          <div className="table-wrap"><table><thead><tr><th>Fonte</th><th>Status</th><th>Projetos Sincronizados</th><th>Última Sinc.</th></tr></thead>
            <tbody>{integrations.map((s: any, i: number) => (
              <tr key={i}><td style={{ fontWeight: 600 }}>{s.source}</td>
                <td><span className={`badge ${s.status === 'completed' ? 'badge-green' : 'badge-yellow'}`}>{s.status}</span></td>
                <td>{s.projects_synced}</td><td>{s.last_sync_at ? new Date(s.last_sync_at).toLocaleString('pt-BR') : 'N/A'}</td></tr>
            ))}</tbody></table></div>
        ) : <p style={{ color: 'var(--cv-text-muted)', textAlign: 'center', padding: '2rem' }}>Nenhuma integração ativa</p>}</div>
      )}

      {activeTab === 'audit' && (
        <div className="card"><div className="table-wrap"><table><thead><tr><th>Ação</th><th>Recurso</th><th>Usuário</th><th>Data</th></tr></thead>
          <tbody>{auditLog.map((l: any) => (
            <tr key={l.id}><td style={{ fontWeight: 600 }}>{l.action}</td><td>{l.resource_type} {l.resource_id ? `#${l.resource_id}` : ''}</td>
              <td>{l.user_name}</td><td style={{ fontSize: '0.8rem' }}>{new Date(l.created_at).toLocaleString('pt-BR')}</td></tr>
          ))}</tbody></table></div></div>
      )}
    </div>
  );
}
