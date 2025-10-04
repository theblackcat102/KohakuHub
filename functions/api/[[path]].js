import { proxyToAPI } from '../_proxy.js';

export async function onRequest(context) {
  // Strip /api prefix if your backend doesn't expect it
  // Remove the second parameter if your backend expects /api in the path
  return proxyToAPI(context);
}
