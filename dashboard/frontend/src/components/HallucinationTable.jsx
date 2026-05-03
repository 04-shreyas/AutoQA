import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function HallucinationTable({ results = [] }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  const getRiskColor = (riskLevel) => {
    switch (riskLevel?.toUpperCase()) {
      case 'HIGH':
        return 'bg-red-500/20 text-red-400 border-l-4 border-red-500';
      case 'MEDIUM':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'LOW':
        return 'bg-green-500/20 text-green-400';
      default:
        return 'bg-gray-800 text-gray-400';
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
      <h3 className="text-xl font-bold text-white mb-6">Hallucination Detection Results</h3>

      <div className="space-y-3">
        {results.length === 0 ? (
          <p className="text-gray-400 text-center py-8">No results available</p>
        ) : (
          results.map((result, idx) => (
            <div
              key={idx}
              className={`rounded-lg p-4 cursor-pointer transition ${getRiskColor(result.risk_level)}`}
            >
              <div
                className="flex items-start justify-between"
                onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
              >
                <div className="flex-1">
                  <p className="font-semibold text-white mb-1">
                    {result.prompt?.substring(0, 100) || 'Prompt'}...
                  </p>
                  <div className="flex gap-4 text-sm">
                    <span>Score: <strong>{result.overall_score?.toFixed(1) || 0}</strong>/100</span>
                    <span>Risk: <strong>{result.risk_level || 'UNKNOWN'}</strong></span>
                    {result.hallucinated && <span className="text-red-400">⚠ Flagged</span>}
                  </div>
                </div>
                <ChevronDown
                  size={20}
                  className={`transition ${expandedIndex === idx ? 'rotate-180' : ''}`}
                />
              </div>

              {/* Expanded Details */}
              {expandedIndex === idx && (
                <div className="mt-4 pt-4 border-t border-current border-opacity-30">
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="text-gray-300 font-medium mb-1">Response:</p>
                      <p className="text-gray-300">{result.response?.substring(0, 300)}</p>
                    </div>
                    {result.hallucinated_claims && (
                      <div>
                        <p className="text-gray-300 font-medium mb-1">Flagged Claims:</p>
                        <ul className="list-disc list-inside text-gray-300">
                          {(Array.isArray(result.hallucinated_claims) ? result.hallucinated_claims : []).map((claim, i) => (
                            <li key={i}>{claim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {result.reasoning && (
                      <div>
                        <p className="text-gray-300 font-medium mb-1">Reasoning:</p>
                        <p className="text-gray-300">{result.reasoning}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
