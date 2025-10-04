import { proxyToAPI } from '../../../_proxy.js';

export async function onRequest(context) {
  return proxyToAPI(context);
}
