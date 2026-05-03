import { useState, useMemo } from 'react';
import { Search, Filter } from 'lucide-react';

export default function TestResultsTable({ results = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  const filteredResults = useMemo(() => {
    return results.filter((result) => {
      const matchSearch = result.name?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = filterStatus === 'all' || result.status === filterStatus;
      return matchSearch && matchStatus;
    });
  }, [results, searchTerm, filterStatus]);

  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
      <h3 className="text-xl font-bold text-white mb-6">Test Results</h3>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 text-gray-500" size={20} />
          <input
            type="text"
            placeholder="Search tests..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
        >
          <option value="all">All Status</option>
          <option value="PASS">Passed</option>
          <option value="FAIL">Failed</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-700">
            <tr className="text-gray-400 text-sm font-medium">
              <th className="text-left py-3 px-4">Test Name</th>
              <th className="text-left py-3 px-4">File</th>
              <th className="text-left py-3 px-4">Status</th>
              <th className="text-left py-3 px-4">Duration</th>
            </tr>
          </thead>
          <tbody>
            {filteredResults.length === 0 ? (
              <tr>
                <td colSpan="4" className="py-8 text-center text-gray-400">
                  No tests found
                </td>
              </tr>
            ) : (
              filteredResults.map((result, idx) => (
                <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="py-4 px-4 text-white font-medium">{result.name}</td>
                  <td className="py-4 px-4 text-gray-400 text-sm">{result.file}</td>
                  <td className="py-4 px-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      result.status === 'PASS'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {result.status}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-gray-400 text-sm">{result.duration || 'N/A'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
