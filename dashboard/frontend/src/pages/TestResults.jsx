import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import TestResultsTable from '../components/TestResultsTable';
import { getTestResults } from '../api/autoqa';

export default function TestResults() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadResults = async () => {
      try {
        const data = await getTestResults();
        setResults(data);
      } catch (error) {
        console.error('Error loading test results:', error);
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading test results...</div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = [
    { name: 'Passed', value: results?.passed || 0, fill: '#22c55e' },
    { name: 'Failed', value: results?.failed || 0, fill: '#ef4444' },
  ];

  return (
    <div className="space-y-8">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h3 className="text-gray-400 text-sm font-medium mb-2">Total Tests</h3>
          <p className="text-3xl font-bold text-white">{results?.total_tests || 0}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 border border-green-500 shadow-green-500/20">
          <h3 className="text-gray-400 text-sm font-medium mb-2">Passed</h3>
          <p className="text-3xl font-bold text-green-400">{results?.passed || 0}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 border border-red-500 shadow-red-500/20">
          <h3 className="text-gray-400 text-sm font-medium mb-2">Failed</h3>
          <p className="text-3xl font-bold text-red-400">{results?.failed || 0}</p>
        </div>
      </div>

      {/* Pass Rate Chart */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <h3 className="text-xl font-bold text-white mb-6">Test Results Overview</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111827',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#fff' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed Table */}
      <TestResultsTable results={results?.test_results || []} />
    </div>
  );
}
