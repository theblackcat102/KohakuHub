/**
 * External token management utilities
 *
 * Stores user's external fallback tokens in localStorage and formats them
 * for the Authorization header in the format: "token|url1,token1|url2,token2"
 */

const STORAGE_KEY = "hf_external_tokens";

/**
 * Get external tokens from localStorage
 * @returns {Array<{url: string, token: string}>} Array of token objects
 */
export function getExternalTokens() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch (err) {
    console.error("Failed to parse external tokens:", err);
    return [];
  }
}

/**
 * Save external tokens to localStorage
 * @param {Array<{url: string, token: string}>} tokens - Array of token objects
 */
export function setExternalTokens(tokens) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  } catch (err) {
    console.error("Failed to save external tokens:", err);
  }
}

/**
 * Add or update an external token
 * @param {string} url - Source URL
 * @param {string} token - Token for this source
 */
export function addExternalToken(url, token) {
  const tokens = getExternalTokens();
  const existing = tokens.findIndex((t) => t.url === url);

  if (existing >= 0) {
    tokens[existing].token = token;
  } else {
    tokens.push({ url, token });
  }

  setExternalTokens(tokens);
}

/**
 * Remove an external token
 * @param {string} url - Source URL
 */
export function removeExternalToken(url) {
  const tokens = getExternalTokens();
  const filtered = tokens.filter((t) => t.url !== url);
  setExternalTokens(filtered);
}

/**
 * Clear all external tokens
 */
export function clearExternalTokens() {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Format Authorization header with external tokens
 * Format: "Bearer token|url1,token1|url2,token2"
 *
 * @param {string|null} authToken - Main authentication token
 * @param {Array<{url: string, token: string}>} externalTokens - External tokens
 * @returns {string} Formatted Authorization header value
 */
export function formatAuthHeader(authToken, externalTokens = []) {
  const parts = [authToken || ""];

  if (externalTokens && externalTokens.length > 0) {
    for (const { url, token } of externalTokens) {
      parts.push(`${url},${token || ""}`);
    }
  }

  return `Bearer ${parts.join("|")}`;
}
