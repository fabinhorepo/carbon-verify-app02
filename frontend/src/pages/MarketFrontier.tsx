import { useState, useEffect, useMemo } from 'react';
import { TrendingDown, TrendingUp, Target, Award, RefreshCw, Star } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface FrontierPoint {
  project_id: number;
  project_name: string;
  project_type: string;
  grade: string;
  price_eur: number;
  rating_score: number;
  is_frontier: boolean;
  is_opportunity: boolean;
}

interface Opportunity {
  project_id: number;
  project_name: string;
  project_type: string;
  grade: string;
  price_eur: number;
  median_price_eur: number;
  discount_pct: number;
  rating_score: number;
  risk_adjusted_cost_eur: number;
  opportunity_score: number;
}

const gradeColors: Record<string, string> = {
  AAA: '#10b981', AA: '#34d399', A: '#6ee7b7', BBB: '#fbbf24', BB: '#f59e0b',
  B: '#f97316', CCC: '#ef4444', CC: '#dc2626', C: '#991b1b', D: '#7f1d1d',
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-gray-900/95 backdrop-blur-sm border border-gray-700 rounded-lg p-3 text-xs">
      <p className="text-white font-medium">{d.project_name}</p>
      <p className="text-gray-400">{d.project_type} · {d.grade}</p>
      <p className="text-emerald-400">€{d.price_eur?.toFixed(2)}/tCO2</p>
      <p className="text-indigo-400">Score: {d.rating_score?.toFixed(1)}/100</p>
      {d.is_frontier && <p className="text-yellow-400 font-semibold mt-1">★ Fronteira Eficiente</p>}
      {d.is_opportunity && <p className="text-green-400 font-semibold mt-1">💎 Oportunidade</p>}
    </div>
  );
};

export default function MarketFrontier() {
  const [data, setData] = useState<{ frontier: FrontierPoint[]; opportunities: Opportunity[]; all_points: FrontierPoint[]; stats: any } | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'chart' | 'opportunities'>('chart');
  const API = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/v1/market/frontier`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const chartData = useMemo(() => {
    if (!data?.all_points) return [];
    return data.all_points.map(p => ({
      ...p,
      x: p.price_eur,
      y: p.rating_score,
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Target className="text-amber-400" /> Price-Quality Frontier
          </h1>
          <p className="text-gray-400 mt-1">Fronteira eficiente preço-qualidade e identificação de oportunidades</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setView('chart')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${view === 'chart' ? 'bg-amber-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
            Gráfico
          </button>
          <button onClick={() => setView('opportunities')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${view === 'opportunities' ? 'bg-amber-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
            Oportunidades ({data?.opportunities?.length || 0})
          </button>
        </div>
      </div>

      {/* Stats */}
      {data?.stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: 'Créditos Analisados', value: data.stats.total_credits_analyzed, icon: <Award size={18} className="text-indigo-400" /> },
            { label: 'Pontos na Fronteira', value: data.stats.frontier_points, icon: <Star size={18} className="text-yellow-400" /> },
            { label: 'Oportunidades', value: data.stats.opportunities_found, icon: <TrendingUp size={18} className="text-emerald-400" /> },
            { label: 'Preço Médio', value: `€${data.stats.avg_price?.toFixed(2)}`, icon: <TrendingDown size={18} className="text-amber-400" /> },
            { label: 'Faixa de Preço', value: `€${data.stats.min_price?.toFixed(0)} - €${data.stats.max_price?.toFixed(0)}`, icon: <RefreshCw size={18} className="text-cyan-400" /> },
          ].map((stat, i) => (
            <div key={i} className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.icon} {stat.label}</div>
              <p className="text-xl font-bold text-white">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-amber-500"></div>
        </div>
      ) : view === 'chart' ? (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-white mb-4">Curva Eficiente — Preço (EUR/tCO2) vs Qualidade (Score)</h2>
          <ResponsiveContainer width="100%" height={450}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" dataKey="x" name="Preço" unit="€" stroke="#9ca3af" fontSize={12}
                label={{ value: 'Preço (EUR/tCO2)', position: 'insideBottom', offset: -20, style: { fill: '#9ca3af', fontSize: 12 } }} />
              <YAxis type="number" dataKey="y" name="Score" stroke="#9ca3af" fontSize={12} domain={[0, 100]}
                label={{ value: 'Score de Qualidade', angle: -90, position: 'insideLeft', offset: 10, style: { fill: '#9ca3af', fontSize: 12 } }} />
              <Tooltip content={<CustomTooltip />} />
              <Scatter name="Créditos" data={chartData} shape="circle">
                {chartData.map((entry, i) => (
                  <Cell key={i}
                    fill={entry.is_frontier ? '#fbbf24' : entry.is_opportunity ? '#10b981' : gradeColors[entry.grade] || '#6b7280'}
                    r={entry.is_frontier ? 8 : entry.is_opportunity ? 7 : 5}
                    stroke={entry.is_frontier ? '#fbbf24' : entry.is_opportunity ? '#10b981' : 'none'}
                    strokeWidth={entry.is_frontier || entry.is_opportunity ? 2 : 0}
                    opacity={entry.is_frontier || entry.is_opportunity ? 1 : 0.7}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500"></span> Fronteira Eficiente</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500"></span> Oportunidade</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-gray-500"></span> Outros</span>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {data?.opportunities?.map((opp, i) => (
            <div key={i} className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 hover:border-emerald-500/30 transition-colors backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-bold border ${
                      ['AAA', 'AA', 'A'].includes(opp.grade) ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : ['BBB', 'BB'].includes(opp.grade) ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-red-500/15 text-red-400 border-red-500/30'
                    }`}>{opp.grade}</span>
                    <h3 className="text-white font-medium">{opp.project_name}</h3>
                    <span className="text-xs text-gray-500">{opp.project_type}</span>
                  </div>
                  <div className="flex items-center gap-6 mt-2 text-sm">
                    <span className="text-emerald-400">€{opp.price_eur.toFixed(2)}/tCO2</span>
                    <span className="text-gray-500">Mediana: €{opp.median_price_eur.toFixed(2)}</span>
                    <span className="text-green-400 font-semibold">{opp.discount_pct.toFixed(1)}% abaixo</span>
                    <span className="text-gray-500">Risk-adj: €{opp.risk_adjusted_cost_eur.toFixed(2)}</span>
                  </div>
                </div>
                <div className="text-right ml-4">
                  <p className="text-2xl font-bold text-emerald-400">{opp.opportunity_score.toFixed(1)}</p>
                  <p className="text-xs text-gray-500">Score Oportunidade</p>
                </div>
              </div>
            </div>
          ))}
          {!data?.opportunities?.length && (
            <div className="text-center text-gray-500 py-12">Nenhuma oportunidade identificada no momento.</div>
          )}
        </div>
      )}
    </div>
  );
}
