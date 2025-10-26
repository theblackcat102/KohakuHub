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

// ============================================================================
// BOARDS API - Real data from file system
// ============================================================================

/**
 * Fetch all boards
 * @returns {Promise<Array>} List of boards with metadata
 */
export async function fetchBoards() {
  const response = await api.get("/boards");
  return response.data;
}

/**
 * Fetch board metadata
 * @param {string} boardId - Board identifier
 * @returns {Promise<Object>} Board metadata
 */
export async function fetchBoardMetadata(boardId) {
  const response = await api.get(`/boards/${boardId}/metadata`);
  return response.data;
}

/**
 * Fetch board summary (metadata + available data)
 * @param {string} boardId - Board identifier
 * @returns {Promise<Object>} Board summary
 */
export async function fetchBoardSummary(boardId) {
  const response = await api.get(`/boards/${boardId}/summary`);
  return response.data;
}

/**
 * Fetch available scalar metrics for a board
 * @param {string} boardId - Board identifier
 * @returns {Promise<Object>} Object with metrics array
 */
export async function fetchAvailableScalars(boardId) {
  const response = await api.get(`/boards/${boardId}/scalars`);
  return response.data;
}

/**
 * Fetch scalar data for a specific metric
 * @param {string} boardId - Board identifier
 * @param {string} metric - Metric name
 * @param {Object} params - Query parameters (limit, etc.)
 * @returns {Promise<Object>} Object with metric name and data array
 */
export async function fetchScalarData(boardId, metric, params = {}) {
  const response = await api.get(`/boards/${boardId}/scalars/${metric}`, {
    params,
  });
  return response.data;
}

/**
 * Fetch available media log names
 * @param {string} boardId - Board identifier
 * @returns {Promise<Object>} Object with media array
 */
export async function fetchAvailableMedia(boardId) {
  const response = await api.get(`/boards/${boardId}/media`);
  return response.data;
}

/**
 * Fetch media data for a specific log name
 * @param {string} boardId - Board identifier
 * @param {string} name - Media log name
 * @param {Object} params - Query parameters (limit, etc.)
 * @returns {Promise<Object>} Object with name and data array
 */
export async function fetchMediaData(boardId, name, params = {}) {
  const response = await api.get(`/boards/${boardId}/media/${name}`, {
    params,
  });
  return response.data;
}

/**
 * Get media file URL
 * @param {string} boardId - Board identifier
 * @param {string} filename - Media filename
 * @returns {string} Media file URL
 */
export function getMediaFileUrl(boardId, filename) {
  return `/api/boards/${boardId}/media/files/${filename}`;
}

/**
 * Fetch available table log names
 * @param {string} boardId - Board identifier
 * @returns {Promise<Object>} Object with tables array
 */
export async function fetchAvailableTables(boardId) {
  const response = await api.get(`/boards/${boardId}/tables`);
  return response.data;
}

/**
 * Fetch table data for a specific log name
 * @param {string} boardId - Board identifier
 * @param {string} name - Table log name
 * @param {Object} params - Query parameters (limit, etc.)
 * @returns {Promise<Object>} Object with name and data array
 */
export async function fetchTableData(boardId, name, params = {}) {
  const response = await api.get(`/boards/${boardId}/tables/${name}`, {
    params,
  });
  return response.data;
}

export default api;
