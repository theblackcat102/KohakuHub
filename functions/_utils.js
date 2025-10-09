/**
 * Shared utilities for KohakuHub Cloudflare Pages Functions
 */

// VPS API origin - override with environment variable
export const getApiOrigin = (env) => env.API_BASE_URL || 'http://hub-api:48888';

/**
 * Check if request is Git Smart HTTP protocol
 * @param {string} pathname - Request pathname
 * @returns {boolean}
 */
function isGitRequest(pathname) {
  return pathname.includes('.git/info/refs') ||
         pathname.includes('.git/git-upload-pack') ||
         pathname.includes('.git/git-receive-pack') ||
         pathname.endsWith('.git/HEAD');
}

/**
 * Proxy request to VPS API server
 * @param {Request} request - Original request
 * @param {object} env - Environment variables
 * @param {string} stripPrefix - Optional prefix to strip from path (e.g., '/api')
 * @returns {Promise<Response>}
 */
export async function proxyToVps(request, env, stripPrefix) {
  const inUrl = new URL(request.url);
  const outUrl = new URL(getApiOrigin(env));

  // Keep path, optionally strip a prefix like "/api"
  const path = stripPrefix
    ? inUrl.pathname.replace(new RegExp(`^${stripPrefix}`), '')
    : inUrl.pathname;

  outUrl.pathname = path;
  outUrl.search = inUrl.search;

  // Pass request through (streams upload/download)
  const resp = await fetch(outUrl.toString(), {
    method: request.method,
    headers: request.headers,
    body: request.body,
    duplex: 'half', // Required for streaming request bodies
  });

  // Adjust headers
  const headers = new Headers(resp.headers);

  // Special handling for Git protocol responses
  if (isGitRequest(inUrl.pathname)) {
    // CRITICAL: Prevent caching for Git protocol!
    headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('X-Accel-Buffering', 'no');
    // Preserve Content-Type from backend (already in resp.headers)
    // DO NOT set CORS headers for Git protocol (breaks git client)
  } else {
    // For non-Git requests, allow same-origin SPA to read responses
    headers.set('Access-Control-Allow-Origin', inUrl.origin);
    headers.set('Access-Control-Allow-Credentials', 'true');
  }

  return new Response(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: headers,
  });
}

/**
 * Handle CORS preflight requests
 * @param {Request} request - Original request
 * @returns {Response}
 */
export function handleOptions(request) {
  const reqHeaders = request.headers.get('Access-Control-Request-Headers') || 'content-type, authorization';
  const reqMethod = request.headers.get('Access-Control-Request-Method') || 'GET,POST,PUT,PATCH,DELETE,OPTIONS';

  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': reqMethod,
      'Access-Control-Allow-Headers': reqHeaders,
      'Access-Control-Max-Age': '86400',
    },
  });
}
