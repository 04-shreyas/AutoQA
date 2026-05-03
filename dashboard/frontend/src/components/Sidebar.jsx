import { Link, useLocation } from 'react-router-dom';
import { Home, Beaker, Search, TrendingUp, Play, Zap } from 'lucide-react';

export default function Sidebar({ healthScore = 85 }) {
  const location = useLocation();

  const navItems = [
    { path: '/', icon: Home, label: 'Overview' },
    { path: '/test-results', icon: Beaker, label: 'Test Results' },
    { path: '/hallucination', icon: Search, label: 'Hallucination Analysis' },
    { path: '/drift', icon: TrendingUp, label: 'Drift Monitor' },
    { path: '/run', icon: Play, label: 'Run New Eval' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">
          AutoQA
        </h2>
        <p className="text-gray-500 text-xs mt-1">Quality Platform</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {navItems.map(({ path, icon: Icon, label }) => (
          <Link
            key={path}
            to={path}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${
              location.pathname === path
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Icon size={20} />
            <span className="font-medium">{label}</span>
          </Link>
        ))}
      </nav>

      {/* Health Score Badge */}
      <div className="p-4 border-t border-gray-800">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-gray-400 text-xs font-medium mb-2">HEALTH SCORE</div>
          <div className="flex items-center gap-2">
            <div className="text-3xl font-bold text-white">{Math.round(healthScore)}</div>
            <div className={`text-xs font-semibold px-2 py-1 rounded ${
              healthScore >= 80
                ? 'bg-green-500/20 text-green-400'
                : healthScore >= 60
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'bg-red-500/20 text-red-400'
            }`}>
              {healthScore >= 80 ? 'Good' : healthScore >= 60 ? 'Fair' : 'Poor'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
