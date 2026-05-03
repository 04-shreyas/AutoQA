import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle } from 'lucide-react';

export default function DriftChart({ driftData = [], regressions = [] }) {
  // Simple trend data for demo
  const trendData = [
    { run: 'Run 1', score: 65 },
    { run: 'Run 2', score: 58 },
    { run: 'Run 3', score: 72 },
    { run: 'Run 4', score: 68 },
  ];

  return (
    <div className="space-y-6">
      {/* Trend Chart */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <h3 className="text-xl font-bold text-white mb-6">Drift Score Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111827',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#fff' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#a855f7"
              strokeWidth={2}
              dot={{ fill: '#a855f7', r: 6 }}
              activeDot={{ r: 8 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Regressions Alert */}
      {regressions && regressions.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-red-400 mt-1" size={20} />
            <div>
              <h4 className="text-red-400 font-semibold mb-2">Performance Regressions Detected</h4>
              <ul className="text-red-400/80 text-sm space-y-1">
                {regressions.map((reg, idx) => (
                  <li key={idx}>• {reg}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h4 className="text-gray-400 text-sm mb-4">Run Comparison</h4>
          <div className="space-y-3 text-white">
            <div className="flex justify-between">
              <span>Score Change:</span>
              <span className="text-purple-400 font-bold">-4.2%</span>
            </div>
            <div className="flex justify-between">
              <span>Latency Change:</span>
              <span className="text-yellow-400 font-bold">+12.5%</span>
            </div>
            <div className="flex justify-between">
              <span>Consistency:</span>
              <span className="text-green-400 font-bold">↑ 3.1%</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h4 className="text-gray-400 text-sm mb-4">Current Status</h4>
          <div className="text-center">
            <div className="text-5xl font-bold text-purple-400 mb-2">{driftData.drift_score || 0}</div>
            <p className="text-gray-400 text-sm">Drift Score</p>
            <div className={`mt-4 inline-block px-3 py-1 rounded text-xs font-semibold ${
              (driftData.drift_score || 0) > 70
                ? 'bg-red-500/20 text-red-400'
                : (driftData.drift_score || 0) > 40
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'bg-green-500/20 text-green-400'
            }`}>
              {(driftData.drift_score || 0) > 70 ? 'Critical' : (driftData.drift_score || 0) > 40 ? 'Warning' : 'Normal'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
