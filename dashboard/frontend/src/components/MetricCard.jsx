import { TrendingUp, TrendingDown } from 'lucide-react';

export default function MetricCard({ title, value, unit = '', trend, color = 'blue' }) {
  const colorClasses = {
    blue: 'border-blue-500 shadow-blue-500/20',
    green: 'border-green-500 shadow-green-500/20',
    yellow: 'border-yellow-500 shadow-yellow-500/20',
    purple: 'border-purple-500 shadow-purple-500/20',
  };

  const trendColorClass = trend && trend > 0 ? 'text-green-400' : 'text-red-400';
  const TrendIcon = trend && trend > 0 ? TrendingUp : TrendingDown;

  return (
    <div className={`bg-gray-900 rounded-xl p-6 border ${colorClasses[color]} shadow-lg transition hover:shadow-xl hover:shadow-${color}-500/30`}>
      <p className="text-gray-400 text-sm font-medium mb-2">{title}</p>
      <div className="flex items-baseline justify-between">
        <div className="text-4xl font-bold text-white">
          {typeof value === 'number' ? value.toFixed(1) : value}
          <span className="text-lg text-gray-400 ml-2">{unit}</span>
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 ${trendColorClass}`}>
            <TrendIcon size={20} />
            <span className="text-sm font-semibold">{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}
