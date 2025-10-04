/**
 * Shared proxy handler for KohakuHub API requests
 * Used by all Cloudflare Pages Functions to proxy requests to the backend API
 */
import { proxyToVps, handleOptions } from './_utils.js';

export async function proxyToAPI(context, stripPrefix) {
  // Handle CORS preflight
  if (context.request.method === 'OPTIONS') {
    return handleOptions(context.request);
  }

  // Proxy to VPS API
  return proxyToVps(context.request, context.env, stripPrefix);
}
