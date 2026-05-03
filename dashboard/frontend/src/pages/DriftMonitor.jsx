import { useState, useEffect } from 'react';
import DriftChart from '../components/DriftChart';
import { getDriftResults } from '../api/autoqa';

export default function DriftMonitor() {
  const [driftData, setDriftData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadResults = async () => {
      try {
        const data = await getDriftResults();
        setDriftData(data);
      } catch (error) {
        console.error('Error loading drift results:', error);
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading drift analysis...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <h2 className="text-2xl font-bold text-white mb-4">Drift Monitor</h2>
        <p className="text-gray-400">
          Track performance changes and detect regressions across evaluation runs.
        </p>
      </div>

      {/* Drift Chart */}
      <DriftChart
        driftData={driftData || {}}
        regressions={driftData?.regressions || []}
      />
    </div>
  );
}
