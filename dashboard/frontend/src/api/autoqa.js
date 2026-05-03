import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const getSummary = async () => {
  const response = await api.get('/summary');
  return response.data;
};

export const getTestResults = async () => {
  const response = await api.get('/test-results');
  return response.data;
};

export const getHallucinationResults = async () => {
  const response = await api.get('/hallucination-results');
  return response.data;
};

export const getDriftResults = async () => {
  const response = await api.get('/drift-results');
  return response.data;
};

export const getLatestReport = async () => {
  const response = await api.get('/latest-report');
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const listRuns = async () => {
  const response = await api.get('/runs');
  return response.data;
};

export const runPipeline = async (targetPath, promptsPath, model) => {
  const response = await api.post('/run', {
    target_path: targetPath,
    prompts_path: promptsPath,
    model: model,
  });
  return response.data;
};

export const getRunStatus = async (runId) => {
  const response = await api.get(`/run-status/${runId}`);
  return response.data;
};
