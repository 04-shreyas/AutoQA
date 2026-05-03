import { useEffect, useState } from 'react';
import { getHallucinationResults } from '../api/autoqa';
import HallucinationTable from '../components/HallucinationTable';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function HallucinationAnalysis() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadResults = async () => {
      try {
        const data = await getHallucinationResults();
        setResults(data.results || []);
      } catch (err) {
        setError('Failed to load hallucination analysis.');
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, []);

  const distribution = results.map((item) => ({
    name: item.test_name,
    score: item.confidence_score * 100,
  }));

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-violet-300">Hallucination Review</p>
          <h1 className="text-3xl font-semibold text-white">Hallucination analysis</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Inspect test outputs, model confidence, and hallucination severity across recent evaluations.
          </p>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <h2 className="text-xl font-semibold text-white">Detected hallucination cases</h2>
          <p className="mt-2 text-sm text-slate-400">
            Review generated tests and identify high-risk hallucinations that require manual validation.
          </p>
          {loading ? (
            <div className="py-20 text-center text-slate-400">Loading results…</div>
          ) : error ? (
            <div className="py-20 text-center text-rose-400">{error}</div>
          ) : (
            <HallucinationTable results={results} />
          )}
        </div>

        <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <h2 className="text-xl font-semibold text-white">Confidence distribution</h2>
          <p className="mt-2 text-sm text-slate-400">
            Model confidence shows how reliably generated tests match known behavior.
          </p>
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distribution.slice(0, 6)}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} interval={0} angle={-30} textAnchor="end" height={80} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="score" fill="#a855f7" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
