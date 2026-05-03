import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from 'recharts';

export default function HealthGauge({ score = 75 }) {
  const data = [{ name: 'Health', value: score, fill: '#8b5cf6' }];
  
  const getColor = () => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#eab308';
    return '#ef4444';
  };

  return (
    <div className="bg-gray-900 rounded-xl p-8 border border-purple-500 shadow-lg shadow-purple-500/20">
      <h3 className="text-gray-400 text-sm font-medium mb-6 text-center">Health Score</h3>
      <ResponsiveContainer width="100%" height={300}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="70%"
          outerRadius="90%"
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background
            dataKey="value"
            cornerRadius={10}
            fill={getColor()}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="text-center mt-6">
        <div className="text-5xl font-bold text-white">{Math.round(score)}</div>
        <div className="text-gray-400 text-sm mt-2">
          {score >= 80 ? '✓ Excellent' : score >= 60 ? '⚠ Good' : '✗ Critical'}
        </div>
      </div>
    </div>
  );
}
