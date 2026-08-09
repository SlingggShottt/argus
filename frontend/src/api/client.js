// Centralized API calls -- components never call fetch() directly, per
// style_guide.md. Relative /api paths: Vite's dev server proxies them to
// FastAPI (see vite.config.js), and a production deploy is expected to
// serve the frontend behind the same reverse proxy as the backend.

async function request(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${response.status}`)
  }
  return response.json()
}

export function getForecast(storeId, itemId) {
  return request(`/api/forecasts/${storeId}/${itemId}`)
}

export function getRisks({ riskType, severity } = {}) {
  const params = new URLSearchParams()
  if (riskType) params.set('risk_type', riskType)
  if (severity) params.set('severity', severity)
  const query = params.toString()
  return request(`/api/risks${query ? `?${query}` : ''}`)
}

export function getRecommendations({ storeId, itemId } = {}) {
  const params = new URLSearchParams()
  if (storeId) params.set('store_id', storeId)
  if (itemId) params.set('item_id', itemId)
  const query = params.toString()
  return request(`/api/recommendations${query ? `?${query}` : ''}`)
}

export function postQuery(question) {
  return request('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
}
