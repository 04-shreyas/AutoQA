import { useEffect, useState } from 'react';
import { getSummary } from '../api/autoqa';
import MetricCard from '../components/MetricCard';
import HealthGauge from '../components/HealthGauge';

export default function Overview() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await getSummary();
        setSummary(data);
      } catch (err) {
        setError('Unable to load summary data.');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-violet-300">AutoQA Dashboard</p>
          <h1 className="text-3xl font-semibold text-white">Overview</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Monitor generated tests, hallucination risk, and data drift across your QA suite.
          </p>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard title="Tests Generated" value={summary?.tests_generated ?? '—'} />
          <MetricCard title="Pass Rate" value={summary ? `${summary.pass_rate}%` : '—'} />
          <MetricCard title="Hallucination Score" value={summary ? `${summary.avg_hallucination_score}%` : '—'} />
          <MetricCard title="Drift Score" value={summary ? `${summary.drift_score}%` : '—'} />
        </div>

        <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-violet-300">System health</p>
              <h2 className="text-xl font-semibold text-white">Quality gauge</h2>
            </div>
            <span className="inline-flex items-center rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">
              Live summary
            </span>
          </div>

          {loading ? (
            <div className="py-20 text-center text-slate-400">Loading dashboard data…</div>
          ) : error ? (
            <div className="py-20 text-center text-rose-400">{error}</div>
          ) : (
            <HealthGauge score={summary?.health_score ?? 0} />
          )}
        </div>
      </div>
    </div>
  );
}
