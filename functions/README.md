# Cloudflare Pages Functions

This directory contains Cloudflare Pages Functions for routing and proxying requests to the KohakuHub backend API.

## How It Works

Cloudflare Pages serves the static frontend and uses Functions to proxy API/backend requests to your origin server.

**Request Flow:**
```
User → Cloudflare Pages (CDN) → Functions (routing) → Your Server (API)
                               ↓
                        Static files served from CDN
```

## Directory Structure

```
functions/
├── _middleware.js                        # Middleware applied to all requests
├── _proxy.js                             # Shared proxy handler
├── _utils.js                             # Proxy utilities with Git protocol support
├── api/[[path]].js                       # Catch-all for /api/* routes
├── org/[[path]].js                       # Organization routes
├── [[repo]].git/                         # Git Smart HTTP protocol
│   ├── info/
│   │   ├── refs.js                       # Service advertisement
│   │   └── lfs/[[path]].js               # Git LFS
│   ├── git-upload-pack.js                # Clone/fetch/pull
│   ├── git-receive-pack.js               # Push
│   └── HEAD.js                           # HEAD reference
├── models/[[namespace]]/[[name]]/resolve/[[path]].js  # Model file downloads
├── datasets/.../resolve/[[path]].js      # Dataset file downloads
├── spaces/.../resolve/[[path]].js        # Space file downloads
└── [[namespace]]/[[name]]/resolve/[[path]].js  # Legacy file downloads
```

## Git Protocol Handling

**Special Configuration for Git:**

Git Smart HTTP requires special handling:
- ✅ **No caching** - Responses must not be cached
- ✅ **Preserve headers** - Content-Type must be preserved
- ✅ **No CORS** - Git clients don't support CORS headers

**Implementation in `_utils.js`:**
```javascript
if (isGitRequest(pathname)) {
  // Prevent caching (critical!)
  headers.set('Cache-Control', 'no-store, no-cache, must-revalidate');
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('X-Accel-Buffering', 'no');
  // NO CORS headers (breaks Git clients)
}
```

## Routes Configuration

**`public/_routes.json`** specifies which paths should be handled by Functions:

```json
{
  "include": [
    "/api/*",
    "/org/*",
    "/*.git/info/refs",          // Git service advertisement
    "/*.git/git-upload-pack",    // Git clone/fetch/pull
    "/*.git/git-receive-pack",   // Git push
    "/*.git/HEAD",               // Git HEAD reference
    "/*.git/info/lfs/*",         // Git LFS
    "/models/*/*/resolve/*",     // File downloads
    ...
  ]
}
```

## Environment Variables

Set in Cloudflare Pages dashboard:

```bash
API_BASE_URL=https://api.your-hub.com  # Your backend API URL
```

If not set, defaults to `http://hub-api:48888` (Docker internal).

## Testing Locally

```bash
# Install Wrangler
npm install -g wrangler

# Test functions locally
wrangler pages dev dist --compatibility-date=2024-01-01

# Test Git clone
git clone http://localhost:8788/namespace/repo.git
```

## Deployment

Functions are automatically deployed with Cloudflare Pages:

1. Push to GitHub
2. Cloudflare Pages builds frontend
3. Functions deployed from `functions/` directory
4. Environment variables applied

## Troubleshooting

**Git clone fails:**
- Check `_routes.json` includes Git paths
- Verify `isGitRequest()` detects Git URLs correctly
- Ensure no caching headers are set
- Check Cloudflare Page Rules don't interfere

**CORS errors:**
- Git protocol should NOT have CORS headers
- Browser requests should have CORS headers
- Check `isGitRequest()` logic

**404 errors:**
- Verify path is in `_routes.json` include list
- Check function file exists for the route pattern
- Verify `API_BASE_URL` environment variable

## Related Documentation

- [docs/Git.md](../docs/Git.md) - Git clone support
- [docs/cloudflare-git-setup.md](../docs/cloudflare-git-setup.md) - Cloudflare configuration
- [Cloudflare Pages Functions Docs](https://developers.cloudflare.com/pages/functions/)

---

**Last Updated:** October 2025
