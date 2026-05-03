import { useState, useEffect } from 'react';
import { Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { runPipeline, getRunStatus } from '../api/autoqa';

export default function RunForm({ onComplete }) {
  const [formData, setFormData] = useState({
    target_path: '.',
    prompts_path: 'data/sample_prompts.json',
    model: 'ollama/qwen2.5-coder:7b',
  });

  const [isRunning, setIsRunning] = useState(false);
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);

  const models = [
    { value: 'ollama/qwen2.5-coder:7b', label: 'Ollama - Qwen 2.5 Coder (7B)' },
    { value: 'google/gemini-2.0-flash', label: 'Google - Gemini 2.0 Flash' },
  ];

  const steps = [
    'Analyzing codebase...',
    'Planning tests...',
    'Generating tests...',
    'Running evaluation...',
  ];

  // Poll status
  useEffect(() => {
    if (!runId) return;

    const interval = setInterval(async () => {
      try {
        const statusData = await getRunStatus(runId);
        setStatus(statusData.status);
        setProgress(statusData.progress || 0);

        if (statusData.status === 'completed') {
          setIsRunning(false);
          clearInterval(interval);
          setTimeout(() => onComplete?.(), 2000);
        } else if (statusData.status === 'failed') {
          setIsRunning(false);
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [runId, onComplete]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsRunning(true);

    try {
      const result = await runPipeline(
        formData.target_path,
        formData.prompts_path,
        formData.model
      );
      setRunId(result.run_id);
      setStatus('running');
      setProgress(0);
    } catch (error) {
      console.error('Error starting pipeline:', error);
      setIsRunning(false);
      alert('Failed to start pipeline: ' + error.message);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {!isRunning ? (
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl p-8 border border-gray-800 shadow-lg space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6">Run New Evaluation</h2>

          <div>
            <label className="block text-gray-300 font-medium mb-2">Target Project Path</label>
            <input
              type="text"
              value={formData.target_path}
              onChange={(e) => setFormData({ ...formData, target_path: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g., ./ or ./src"
            />
          </div>

          <div>
            <label className="block text-gray-300 font-medium mb-2">Prompts File Path</label>
            <input
              type="text"
              value={formData.prompts_path}
              onChange={(e) => setFormData({ ...formData, prompts_path: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g., data/sample_prompts.json"
            />
          </div>

          <div>
            <label className="block text-gray-300 font-medium mb-2">Model</label>
            <select
              value={formData.model}
              onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-purple-500"
            >
              {models.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-4 rounded-lg transition shadow-lg shadow-purple-600/50 flex items-center justify-center gap-2"
          >
            <span>▶</span> Run AutoQA Pipeline
          </button>
        </form>
      ) : (
        <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 shadow-lg">
          <h2 className="text-2xl font-bold text-white mb-8">Running Evaluation...</h2>

          {/* Progress Steps */}
          <div className="space-y-4 mb-8">
            {steps.map((step, idx) => {
              const isActive = idx === Math.floor((progress / 25) % steps.length);
              const isComplete = idx < Math.floor((progress / 25) % steps.length);

              return (
                <div key={idx} className="flex items-center gap-4">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    isComplete
                      ? 'bg-green-500 text-white'
                      : isActive
                      ? 'bg-purple-500 text-white animate-pulse'
                      : 'bg-gray-700 text-gray-400'
                  }`}>
                    {isComplete ? '✓' : isActive ? '⟳' : idx + 1}
                  </div>
                  <span className={isComplete || isActive ? 'text-white' : 'text-gray-400'}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex justify-between mb-2">
              <span className="text-gray-400 text-sm">Progress</span>
              <span className="text-white font-bold">{progress}%</span>
            </div>
            <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Status Message */}
          <div className="text-center text-gray-400">
            <Loader className="inline-block animate-spin mr-2" size={20} />
            {status === 'completed' && (
              <span className="text-green-400">✓ Evaluation complete! Redirecting...</span>
            )}
            {status === 'failed' && (
              <span className="text-red-400">✗ Evaluation failed</span>
            )}
            {status === 'running' && (
              <span>This may take a few minutes...</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
