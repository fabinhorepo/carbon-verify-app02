import { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import api from '../utils/api';

export default function Reports() {
  const [reports, setReports] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [form, setForm] = useState({ name: '', report_type: 'portfolio', format: 'json' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.get('/reports').then(r => setReports(r.data)).catch(() => {});
    api.get('/reports/templates').then(r => setTemplates(r.data)).catch(() => {});
  }, []);

  const createReport = async () => {
    setCreating(true);
    try {
      await api.post('/reports', form);
      api.get('/reports').then(r => setReports(r.data));
    } catch (e) {} finally { setCreating(false); }
  };

  const statusBadge = (s: string) => s === 'completed' ? 'badge-green' : s === 'failed' ? 'badge-red' : 'badge-yellow';

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Relatórios</h1><p className="page-subtitle">Gere e exporte relatórios</p></div>

      {/* Templates */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title" style={{ marginBottom: '1rem' }}>Templates Disponíveis</div>
        <div className="grid-3">
          {templates.map(t => (
            <div key={t.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setForm({ ...form, report_type: t.type, name: t.name })}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.25rem' }}>{t.name}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)' }}>{t.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Generator */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title" style={{ marginBottom: '1rem' }}>Gerar Relatório</div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Nome</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={{ width: '250px' }} /></div>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Tipo</label>
            <select value={form.report_type} onChange={e => setForm({ ...form, report_type: e.target.value })}>
              <option value="portfolio">Portfólio</option><option value="due_diligence">Due Diligence</option>
              <option value="fraud">Fraude</option><option value="esg">ESG</option><option value="executive">Executivo</option>
            </select></div>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Formato</label>
            <select value={form.format} onChange={e => setForm({ ...form, format: e.target.value })}>
              <option value="json">JSON</option><option value="csv">CSV</option><option value="pdf">PDF</option>
            </select></div>
          <button className="btn btn-primary" onClick={createReport} disabled={creating || !form.name}>
            {creating ? 'Gerando...' : 'Gerar Relatório'}
          </button>
        </div>
      </div>

      {/* History */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}>Relatórios Gerados</div>
        {reports?.items?.length > 0 ? (
          <div className="table-wrap"><table><thead><tr><th>Nome</th><th>Tipo</th><th>Formato</th><th>Status</th><th>Data</th></tr></thead>
            <tbody>{reports.items.map((r: any) => (
              <tr key={r.id}><td style={{ fontWeight: 600 }}><FileText size={14} style={{ display: 'inline', marginRight: '0.35rem' }} />{r.name}</td>
                <td><span className="badge badge-blue">{r.report_type}</span></td><td>{r.format?.toUpperCase()}</td>
                <td><span className={`badge ${statusBadge(r.status)}`}>{r.status}</span></td>
                <td style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)' }}>{new Date(r.created_at).toLocaleString('pt-BR')}</td></tr>
            ))}</tbody></table></div>
        ) : <p style={{ color: 'var(--cv-text-muted)', textAlign: 'center', padding: '2rem' }}>Nenhum relatório gerado ainda</p>}
      </div>
    </div>
  );
}
