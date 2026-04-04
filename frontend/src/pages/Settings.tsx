import { useEffect, useState } from 'react';
import { Save, UserPlus, X, Check } from 'lucide-react';
import api from '../utils/api';

export default function SettingsPage() {
  const [org, setOrg] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('org');

  // Org edit state
  const [editingOrg, setEditingOrg] = useState(false);
  const [orgForm, setOrgForm] = useState({ name: '', slug: '', plan: '' });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // Add member state
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberForm, setMemberForm] = useState({ email: '', full_name: '', password: '', role: 'analyst' });
  const [addingMember, setAddingMember] = useState(false);
  const [memberMsg, setMemberMsg] = useState('');

  useEffect(() => {
    api.get('/organizations/me').then(r => { setOrg(r.data); setOrgForm({ name: r.data.name, slug: r.data.slug, plan: r.data.plan || 'Starter' }); }).catch(() => {});
    api.get('/organizations/me/members').then(r => setMembers(r.data)).catch(() => {});
    api.get('/integrations/status').then(r => setIntegrations(r.data)).catch(() => {});
    api.get('/organizations/me/audit-log').then(r => setAuditLog(r.data)).catch(() => {});
  }, []);

  const handleOrgSave = async () => {
    setSaving(true); setSaveMsg('');
    try {
      const { data } = await api.put('/organizations/me', orgForm);
      setOrg(data);
      setEditingOrg(false);
      setSaveMsg('✅ Organização atualizada com sucesso');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e: any) {
      setSaveMsg(`❌ ${e.response?.data?.detail || 'Erro ao salvar'}`);
    } finally { setSaving(false); }
  };

  const handleAddMember = async () => {
    setAddingMember(true); setMemberMsg('');
    try {
      const { data } = await api.post('/organizations/me/members', memberForm);
      setMembers([...members, data]);
      setShowAddMember(false);
      setMemberForm({ email: '', full_name: '', password: '', role: 'analyst' });
      setMemberMsg('✅ Membro adicionado com sucesso');
      setTimeout(() => setMemberMsg(''), 3000);
    } catch (e: any) {
      setMemberMsg(`❌ ${e.response?.data?.detail || 'Erro ao adicionar membro'}`);
    } finally { setAddingMember(false); }
  };

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Configurações</h1></div>
      <div className="tabs">
        {[['org', 'Organização'], ['members', 'Membros'], ['integrations', 'Integrações'], ['audit', 'Log de Auditoria']].map(([k, v]) => (
          <div key={k} className={`tab ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{v}</div>
        ))}
      </div>

      {/* ─── Organization Tab ─────────────────────────────────── */}
      {activeTab === 'org' && org && (
        <div className="card">
          {saveMsg && (
            <div style={{ padding: '0.75rem', marginBottom: '1rem', borderRadius: '8px', background: saveMsg.startsWith('✅') ? 'rgba(52, 211, 153, 0.1)' : 'rgba(248, 113, 113, 0.1)', textAlign: 'center', fontSize: '0.85rem' }}>
              {saveMsg}
            </div>
          )}

          {!editingOrg ? (
            <>
              <div className="grid-2">
                {[
                  ['Nome', org.name],
                  ['Slug', org.slug],
                  ['API Key', org.api_key ? `${org.api_key.slice(0, 20)}...` : 'Não gerada'],
                  ['Plano', org.plan || 'Starter'],
                  ['Locale', org.locale || 'pt-BR'],
                  ['Rate Limit', `${org.rate_limit || 120} req/min`],
                ].map(([k, v]) => (
                  <div key={k as string} style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k}</div>
                    <div style={{ fontWeight: 600, marginTop: '0.25rem' }}>{v}</div>
                  </div>
                ))}
              </div>
              <button className="btn btn-primary" style={{ marginTop: '1.5rem' }} onClick={() => setEditingOrg(true)}>
                Editar Organização
              </button>
            </>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Nome da Organização</label>
                  <input value={orgForm.name} onChange={e => setOrgForm({ ...orgForm, name: e.target.value })} />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Slug</label>
                  <input value={orgForm.slug} onChange={e => setOrgForm({ ...orgForm, slug: e.target.value })} />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Plano</label>
                  <select value={orgForm.plan} onChange={e => setOrgForm({ ...orgForm, plan: e.target.value })}>
                    <option value="free">Free</option>
                    <option value="starter">Starter</option>
                    <option value="professional">Professional</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>API Key</label>
                  <input value={org.api_key || 'Não gerada'} disabled style={{ opacity: 0.5 }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button className="btn btn-primary" onClick={handleOrgSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Save size={16} /> {saving ? 'Salvando...' : 'Salvar Alterações'}
                </button>
                <button className="btn" onClick={() => { setEditingOrg(false); setOrgForm({ name: org.name, slug: org.slug, plan: org.plan || 'Starter' }); }}>
                  Cancelar
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ─── Members Tab ──────────────────────────────────────── */}
      {activeTab === 'members' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div className="card-title" style={{ marginBottom: 0 }}>Membros da Organização</div>
            <button className="btn btn-primary" onClick={() => setShowAddMember(!showAddMember)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}>
              <UserPlus size={16} /> Adicionar Membro
            </button>
          </div>

          {memberMsg && (
            <div style={{ padding: '0.75rem', marginBottom: '1rem', borderRadius: '8px', background: memberMsg.startsWith('✅') ? 'rgba(52, 211, 153, 0.1)' : 'rgba(248, 113, 113, 0.1)', textAlign: 'center', fontSize: '0.85rem' }}>
              {memberMsg}
            </div>
          )}

          {/* Add Member Form */}
          {showAddMember && (
            <div className="card" style={{ marginBottom: '1rem', borderLeft: '3px solid var(--cv-accent)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Novo Membro</div>
                <button onClick={() => setShowAddMember(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cv-text-muted)' }}>
                  <X size={18} />
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.2rem' }}>Nome Completo</label>
                  <input value={memberForm.full_name} onChange={e => setMemberForm({ ...memberForm, full_name: e.target.value })} placeholder="Ex: Maria Silva" />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.2rem' }}>Email</label>
                  <input type="email" value={memberForm.email} onChange={e => setMemberForm({ ...memberForm, email: e.target.value })} placeholder="maria@empresa.com" />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.2rem' }}>Senha Inicial</label>
                  <input type="password" value={memberForm.password} onChange={e => setMemberForm({ ...memberForm, password: e.target.value })} placeholder="Mínimo 6 caracteres" />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.2rem' }}>Cargo</label>
                  <select value={memberForm.role} onChange={e => setMemberForm({ ...memberForm, role: e.target.value })}>
                    <option value="admin">Admin</option>
                    <option value="analyst">Analista</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
              <button className="btn btn-primary" style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
                onClick={handleAddMember} disabled={addingMember || !memberForm.email || !memberForm.full_name || !memberForm.password}>
                <Check size={16} /> {addingMember ? 'Adicionando...' : 'Confirmar Adição'}
              </button>
            </div>
          )}

          <div className="table-wrap">
            <table>
              <thead><tr><th>Nome</th><th>Email</th><th>Cargo</th><th>Status</th></tr></thead>
              <tbody>
                {members.map((m: any) => (
                  <tr key={m.id}>
                    <td style={{ fontWeight: 600 }}>{m.full_name}</td>
                    <td>{m.email}</td>
                    <td><span className="badge badge-blue">{m.role}</span></td>
                    <td><span className={`badge ${m.is_active ? 'badge-green' : 'badge-red'}`}>{m.is_active ? 'Ativo' : 'Inativo'}</span></td>
                  </tr>
                ))}
                {members.length === 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--cv-text-muted)' }}>Nenhum membro encontrado</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── Integrations Tab ─────────────────────────────────── */}
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

      {/* ─── Audit Log Tab ─────────────────────────────────────── */}
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
