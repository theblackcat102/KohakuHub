// Inline proxy utilities to avoid Cloudflare Pages Functions bundler issues

const getApiOrigin = (env) => env.API_BASE_URL || 'http://hub-api:48888';

function isGitRequest(pathname) {
  return pathname.includes('.git/info/refs') ||
         pathname.includes('.git/git-upload-pack') ||
         pathname.includes('.git/git-receive-pack') ||
         pathname.endsWith('.git/HEAD');
}

async function proxyToVps(request, env) {
  const inUrl = new URL(request.url);
  const outUrl = new URL(getApiOrigin(env));

  outUrl.pathname = inUrl.pathname;
  outUrl.search = inUrl.search;

  const resp = await fetch(outUrl.toString(), {
    method: request.method,
    headers: request.headers,
    body: request.body,
    duplex: 'half',
  });

  const headers = new Headers(resp.headers);

  if (isGitRequest(inUrl.pathname)) {
    headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('X-Accel-Buffering', 'no');
  } else {
    headers.set('Access-Control-Allow-Origin', inUrl.origin);
    headers.set('Access-Control-Allow-Credentials', 'true');
  }

  return new Response(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: headers,
  });
}

function handleOptions(request) {
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

export async function onRequest(context) {
  if (context.request.method === 'OPTIONS') {
    return handleOptions(context.request);
  }
  return proxyToVps(context.request, context.env);
}
