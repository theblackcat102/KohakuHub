/**
 * Dataset Viewer API Client
 *
 * Minimal API client for dataset preview backend.
 * No authentication required - relies on S3 presigned URLs.
 */

import axios from "axios";

const API_BASE = "/api/dataset-viewer";

/**
 * Preview a dataset file
 *
 * @param {string} url - S3 presigned URL or any HTTP(S) URL
 * @param {Object} options - Preview options
 * @param {string} options.format - File format (csv, json, jsonl, parquet, tar)
 * @param {number} options.maxRows - Maximum rows to return (default: 1000)
 * @param {string} options.delimiter - CSV delimiter (default: ",")
 * @returns {Promise<Object>} Preview data
 */
export async function previewFile(url, options = {}) {
  const { format, maxRows = 1000, delimiter = "," } = options;

  const response = await axios.post(`${API_BASE}/preview`, {
    url,
    format,
    max_rows: maxRows,
    delimiter,
  });

  return response.data;
}

/**
 * List files in TAR archive
 *
 * @param {string} url - TAR file URL
 * @returns {Promise<Object>} File listing
 */
export async function listTARFiles(url) {
  const response = await axios.post(`${API_BASE}/tar/list`, { url });
  return response.data;
}

/**
 * Extract file from TAR archive
 *
 * @param {string} url - TAR file URL
 * @param {string} fileName - File name to extract
 * @returns {Promise<Blob>} File content
 */
export async function extractTARFile(url, fileName) {
  const response = await axios.post(
    `${API_BASE}/tar/extract`,
    {
      url,
      file_name: fileName,
    },
    {
      responseType: "blob",
    },
  );

  return response.data;
}

/**
 * Execute SQL query on dataset
 *
 * @param {string} url - Dataset file URL
 * @param {string} query - SQL query to execute
 * @param {Object} options - Query options
 * @param {string} options.format - File format
 * @param {number} options.maxRows - Max rows to return
 * @returns {Promise<Object>} Query results
 */
export async function executeSQLQuery(url, query, options = {}) {
  const { format, maxRows = 10000 } = options;

  const response = await axios.post(`${API_BASE}/sql`, {
    url,
    query, // Query in body, not URL!
    format,
    max_rows: maxRows,
  });

  return response.data;
}

/**
 * Get rate limit statistics
 *
 * @returns {Promise<Object>} Rate limit stats
 */
export async function getRateLimitStats() {
  const response = await axios.get(`${API_BASE}/rate-limit`);
  return response.data;
}

/**
 * Detect file format from filename
 *
 * @param {string} filename - File name
 * @returns {string|null} Format (csv, jsonl, parquet, tar) or null
 *
 * Note: JSON format is NOT supported (requires loading entire file).
 * Use JSONL instead for streaming support.
 */
export function detectFormat(filename) {
  const lower = filename.toLowerCase();

  if (lower.endsWith(".csv")) return "csv";
  if (lower.endsWith(".tsv")) return "tsv";
  if (lower.endsWith(".jsonl") || lower.endsWith(".ndjson")) return "jsonl";
  if (lower.endsWith(".parquet")) return "parquet";
  if (
    lower.endsWith(".tar") ||
    lower.endsWith(".tar.gz") ||
    lower.endsWith(".tgz") ||
    lower.endsWith(".tar.bz2")
  ) {
    return "tar";
  }
  // JSON format deliberately excluded - requires full file download

  return null;
}

/**
 * Format bytes to human-readable string
 *
 * @param {number} bytes - Bytes
 * @returns {string} Formatted string (e.g., "1.5 MB")
 */
export function formatBytes(bytes) {
  if (bytes === 0) return "0 Bytes";
  if (!bytes) return "Unknown";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}
