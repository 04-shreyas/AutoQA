import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Overview from './pages/Overview';
import TestResults from './pages/TestResults';
import HallucinationAnalysis from './pages/HallucinationAnalysis';
import DriftMonitor from './pages/DriftMonitor';
import RunNewEval from './pages/RunNewEval';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <Sidebar healthScore={82} />
        <div className="ml-64 min-h-screen">
          <div className="px-6 py-6">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/test-results" element={<TestResults />} />
              <Route path="/hallucination" element={<HallucinationAnalysis />} />
              <Route path="/drift" element={<DriftMonitor />} />
              <Route path="/run" element={<RunNewEval />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
