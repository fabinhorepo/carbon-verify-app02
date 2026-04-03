import { useState, useEffect } from 'react';
import { Scale, ArrowUpDown, AlertTriangle, Calculator, BarChart3 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const gradeColors: Record<string, string> = {
  AAA: '#10b981', AA: '#34d399', A: '#6ee7b7', BBB: '#fbbf24', BB: '#f59e0b',
  B: '#f97316', CCC: '#ef4444', CC: '#dc2626', C: '#991b1b', D: '#7f1d1d',
};

export default function RiskAdjustedPortfolio() {
  const [metrics, setMetrics] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [targetImpact, setTargetImpact] = useState(100000);
  const [loading, setLoading] = useState(true);
  const API = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/api/v1/portfolios`).then(r => r.json()),
    ]).then(([portfolios]) => {
      if (portfolios.length > 0) {
        const pid = portfolios[0].id;
        Promise.all([
          fetch(`${API}/api/v1/portfolios/${pid}/metrics`).then(r => r.json()),
          fetch(`${API}/api/v1/portfolios/${pid}/risk-adjusted?target_impact=${targetImpact}`).then(r => r.json()),
        ]).then(([m, r]) => {
          setMetrics(m);
          setRiskData(r);
          setLoading(false);
        });
      } else {
        setLoading(false);
      }
    }).catch(() => setLoading(false));
  }, [targetImpact]);

  const gradeChartData = metrics?.grade_distribution
    ? Object.entries(metrics.grade_distribution).map(([grade, qty]) => ({
        grade, qty: qty as number, fill: gradeColors[grade] || '#6b7280',
      }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Scale className="text-cyan-400" /> Toneladas Ajustadas ao Risco
          </h1>
          <p className="text-gray-400 mt-1">Cálculo BeZero-style: quanto carbono seu portfólio realmente compensa</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-cyan-500"></div>
        </div>
      ) : metrics && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 backdrop-blur-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Toneladas Nominais</p>
              <p className="text-3xl font-bold text-white mt-2">{metrics.nominal_tonnes?.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">tCO2e compradas</p>
            </div>
            <div className="bg-gray-800/50 border border-cyan-500/30 rounded-xl p-5 backdrop-blur-sm">
              <p className="text-xs text-cyan-400 uppercase tracking-wider">Toneladas Risk-Adjusted</p>
              <p className="text-3xl font-bold text-cyan-400 mt-2">{metrics.risk_adjusted_tonnes?.toLocaleString()}</p>
              <p className="text-xs text-gray-500 mt-1">tCO2e efetivas</p>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 backdrop-blur-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Fator de Desconto Médio</p>
              <p className="text-3xl font-bold text-white mt-2">{(metrics.discount_factor_avg * 100).toFixed(1)}%</p>
              <p className="text-xs text-gray-500 mt-1">eficiência do portfólio</p>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 backdrop-blur-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Rating do Portfólio</p>
              <p className={`text-3xl font-bold mt-2 ${
                ['AAA', 'AA', 'A'].includes(metrics.portfolio_grade) ? 'text-emerald-400' :
                ['BBB', 'BB'].includes(metrics.portfolio_grade) ? 'text-amber-400' : 'text-red-400'
              }`}>{metrics.portfolio_grade}</p>
              <p className="text-xs text-gray-500 mt-1">score {metrics.avg_quality_score?.toFixed(1)}/100</p>
            </div>
          </div>

          {/* Visual: Nominal vs Risk-Adjusted */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <ArrowUpDown size={18} className="text-cyan-400" /> Comparação: Nominal vs Risk-Adjusted
            </h2>
            <div className="flex items-center gap-8">
              <div className="flex-1">
                <div className="relative">
                  <div className="h-12 bg-gray-700 rounded-lg overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-gray-500 to-gray-400 rounded-lg flex items-center justify-center text-white font-semibold text-sm"
                      style={{ width: '100%' }}>
                      {metrics.nominal_tonnes?.toLocaleString()} tCO2e (Nominal)
                    </div>
                  </div>
                  <div className="h-12 bg-gray-700 rounded-lg overflow-hidden mt-2">
                    <div className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-lg flex items-center justify-center text-white font-semibold text-sm"
                      style={{ width: `${(metrics.discount_factor_avg || 0) * 100}%` }}>
                      {metrics.risk_adjusted_tonnes?.toLocaleString()} tCO2e (Risk-Adjusted)
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <p className="text-xs text-gray-400">
                    <AlertTriangle size={12} className="inline mr-1 text-amber-400" />
                    Perda por risco: {((1 - (metrics.discount_factor_avg || 0)) * 100).toFixed(1)}% das toneladas
                  </p>
                  <p className="text-xs text-gray-400">
                    Diferença: {((metrics.nominal_tonnes || 0) - (metrics.risk_adjusted_tonnes || 0)).toLocaleString()} tCO2e
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Grade Distribution Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 size={18} className="text-indigo-400" /> Distribuição por Rating
              </h2>
              {gradeChartData.length > 0 && (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={gradeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="grade" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#fff' }} />
                    <Bar dataKey="qty" name="Créditos" radius={[4, 4, 0, 0]}>
                      {gradeChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Target Impact Calculator */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Calculator size={18} className="text-amber-400" /> Simulador de Impacto
              </h2>
              <p className="text-sm text-gray-400 mb-4">
                Quantos créditos nominais você precisa comprar para atingir um impacto climático real?
              </p>
              <label className="block text-sm text-gray-400 mb-2">Meta de impacto (tCO2e)</label>
              <input type="number" value={targetImpact} onChange={e => setTargetImpact(Number(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white mb-4 focus:ring-2 focus:ring-cyan-500 focus:border-transparent" />

              {riskData?.grade_breakdown && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm border-b border-gray-700 pb-2">
                    <span className="text-gray-400">Total nominal necessário:</span>
                    <span className="text-white font-bold">{riskData.total_nominal_needed?.toLocaleString()} tCO2e</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Fator de sobre-compra:</span>
                    <span className="text-amber-400 font-bold">{riskData.over_purchase_ratio?.toFixed(2)}x</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-3">
                    Com a composição atual do portfólio, você precisa comprar {riskData.over_purchase_ratio?.toFixed(2)}x mais créditos
                    do que sua meta para compensar o risco de não-entrega.
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
