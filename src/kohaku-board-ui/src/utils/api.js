import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

/**
 * Fetch experiments list
 * @returns {Promise<Array>}
 */
export async function fetchExperiments() {
  const response = await api.get("/experiments");
  return response.data;
}

/**
 * Fetch experiment details
 * @param {string} experimentId
 * @returns {Promise<Object>}
 */
export async function fetchExperiment(experimentId) {
  const response = await api.get(`/experiments/${experimentId}`);
  return response.data;
}

/**
 * Fetch metrics for an experiment
 * @param {string} experimentId
 * @param {Object} params - Query parameters (metric names, step range, etc.)
 * @returns {Promise<Object>}
 */
export async function fetchMetrics(experimentId, params = {}) {
  const response = await api.get(`/experiments/${experimentId}/metrics`, {
    params,
  });
  return response.data;
}

/**
 * Fetch histogram data
 * @param {string} experimentId
 * @param {string} histogramName
 * @returns {Promise<Object>}
 */
export async function fetchHistogram(experimentId, histogramName) {
  const response = await api.get(
    `/experiments/${experimentId}/histograms/${histogramName}`,
  );
  return response.data;
}

/**
 * Fetch table data
 * @param {string} experimentId
 * @param {string} tableName
 * @returns {Promise<Object>}
 */
export async function fetchTable(experimentId, tableName) {
  const response = await api.get(
    `/experiments/${experimentId}/tables/${tableName}`,
  );
  return response.data;
}

/**
 * Generate mock data configuration
 * @param {Object} config - Mock data configuration
 * @returns {Promise<Object>}
 */
export async function generateMockData(config) {
  const response = await api.post("/mock/generate", config);
  return response.data;
}

export default api;
