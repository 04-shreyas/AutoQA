import { useState, useEffect } from 'react';
import { Loader } from 'lucide-react';
import { runPipeline, getRunStatus } from '../api/autoqa';

export default function RunForm() {
  const [formData, setFormData] = useState({
    target_path: './agents',
    prompts_path: 'data/sample_prompts.json',
    model: 'ollama/qwen2.5-coder:7b',
  });

  const [isRunning, setIsRunning] = useState(false);
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [failed, setFailed] = useState(false);

  const models = [
    { value: 'ollama/qwen2.5-coder:7b', label: 'Ollama - Qwen 2.5 Coder (7B)' },
    { value: 'google/gemini-2.0-flash', label: 'Google - Gemini 2.0 Flash' },
  ];

  const steps = [
    'Analyzing codebase...',
    'Planning tests...',
    'Generating tests...',
    'Running evaluation...',
    'Detecting hallucinations...',
    'Analyzing drift...',
    'Writing report...',
  ];

  // Simulate step progression while pipeline runs
  useEffect(() => {
    if (!isRunning || completed || failed) return;

    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < steps.length - 1) return prev + 1;
        return prev;
      });
    }, 30000); // advance a step every 30 seconds

    return () => clearInterval(stepInterval);
  }, [isRunning, completed, failed]);

  // Poll run status
  useEffect(() => {
    if (!runId) return;

    const interval = setInterval(async () => {
      try {
        const statusData = await getRunStatus(runId);
        setStatus(statusData.status);

        if (statusData.status === 'completed') {
          setCompleted(true);
          setIsRunning(false);
          setCurrentStep(steps.length - 1);
          clearInterval(interval);
        } else if (statusData.status === 'failed') {
          setFailed(true);
          setIsRunning(false);
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [runId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsRunning(true);
    setCompleted(false);
    setFailed(false);
    setCurrentStep(0);
    setRunId(null);
    setStatus(null);

    try {
      const result = await runPipeline(
        formData.target_path,
        formData.prompts_path,
        formData.model
      );
      setRunId(result.run_id);
      setStatus('running');
    } catch (error) {
      console.error('Error starting pipeline:', error);
      setIsRunning(false);
      setFailed(true);
      alert('Failed to start pipeline: ' + error.message);
    }
  };

  const handleReset = () => {
    setIsRunning(false);
    setCompleted(false);
    setFailed(false);
    setCurrentStep(0);
    setRunId(null);
    setStatus(null);
  };

  return (
    <div className="max-w-2xl mx-auto">
      {!isRunning && !completed ? (
        <form
          onSubmit={handleSubmit}
          className="bg-gray-900 rounded-xl p-8 border border-gray-800 shadow-lg space-y-6"
        >
          <h2 className="text-2xl font-bold text-white mb-6">Run New Evaluation</h2>

          <div>
            <label className="block text-gray-300 font-medium mb-2">
              Target Project Path
            </label>
            <input
              type="text"
              value={formData.target_path}
              onChange={(e) =>
                setFormData({ ...formData, target_path: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g., ./agents or ./src"
            />
            <p className="text-gray-500 text-xs mt-1">
              Use ./agents to analyze the AutoQA agents folder
            </p>
          </div>

          <div>
            <label className="block text-gray-300 font-medium mb-2">
              Prompts File Path
            </label>
            <input
              type="text"
              value={formData.prompts_path}
              onChange={(e) =>
                setFormData({ ...formData, prompts_path: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g., data/sample_prompts.json"
            />
          </div>

          <div>
            <label className="block text-gray-300 font-medium mb-2">Model</label>
            <select
              value={formData.model}
              onChange={(e) =>
                setFormData({ ...formData, model: e.target.value })
              }
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
      ) : completed ? (
        <div className="bg-gray-900 rounded-xl p-8 border border-green-800 shadow-lg text-center">
          <div className="text-green-400 text-6xl mb-4">✓</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Evaluation Complete!
          </h2>
          <p className="text-gray-400 mb-6">
            All agents finished successfully. Check the other pages for results.
          </p>
          <button
            onClick={handleReset}
            className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-lg transition"
          >
            Run Another Evaluation
          </button>
        </div>
      ) : failed ? (
        <div className="bg-gray-900 rounded-xl p-8 border border-red-800 shadow-lg text-center">
          <div className="text-red-400 text-6xl mb-4">✗</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Evaluation Failed
          </h2>
          <p className="text-gray-400 mb-6">
            Something went wrong. Check the terminal for error details.
          </p>
          <button
            onClick={handleReset}
            className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-lg transition"
          >
            Try Again
          </button>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 shadow-lg">
          <h2 className="text-2xl font-bold text-white mb-8">
            Running Evaluation...
          </h2>

          {/* Steps */}
          <div className="space-y-4 mb-8">
            {steps.map((step, idx) => {
              const isComplete = idx < currentStep;
              const isActive = idx === currentStep;

              return (
                <div key={idx} className="flex items-center gap-4">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                      isComplete
                        ? 'bg-green-500 text-white'
                        : isActive
                        ? 'bg-purple-500 text-white animate-pulse'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {isComplete ? '✓' : isActive ? '⟳' : idx + 1}
                  </div>
                  <span
                    className={
                      isComplete || isActive ? 'text-white' : 'text-gray-400'
                    }
                  >
                    {step}
                  </span>
                  {isActive && (
                    <Loader
                      className="ml-auto animate-spin text-purple-400"
                      size={16}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Status */}
          <div className="text-center text-gray-400 text-sm">
            <Loader className="inline-block animate-spin mr-2" size={16} />
            Pipeline is running... this takes 8–15 minutes with a local model.
            <br />
            <span className="text-xs text-gray-500 mt-1 block">
              You can monitor progress in the terminal.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}