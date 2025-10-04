/**
 * Middleware that runs before all function routes
 * Useful for adding common headers like CORS
 */
export async function onRequest(context) {
  // Let route handlers run first
  const response = await context.next();

  // Add common headers for all proxied responses
  response.headers.set('Access-Control-Allow-Credentials', 'true');

  return response;
}
