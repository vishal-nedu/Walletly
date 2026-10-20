const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function getMessage(data, fallback) {
  if (typeof data === 'string' && data.trim()) return data.replace(/^"|"$/g, '');
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
    if (data.error && typeof data.error.message === 'string') return data.error.message;
    if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || 'Invalid input').join(', ');
  }
  return fallback;
}

async function parseResponse(response) {
  const rawText = await response.text();
  let data = null;
  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = rawText;
    }
  }
  if (!response.ok) {
    throw new ApiError(getMessage(data, `Request failed (${response.status})`), response.status, data);
  }
  return data;
}

function announceUnauthorized() {
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
  window.dispatchEvent(new Event('walletly:session-expired'));
}

async function refreshAccessToken() {
  const refreshToken = sessionStorage.getItem('refresh_token');
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const data = await parseResponse(response);
    if (!data?.access_token) return false;
    sessionStorage.setItem('access_token', data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function request(path, { method = 'GET', body, headers = {}, auth = true, idempotencyKey, retryAuth = true } = {}) {
  const requestHeaders = { ...headers };
  if (body !== undefined) requestHeaders['Content-Type'] = 'application/json';
  if (auth) {
    const token = sessionStorage.getItem('access_token');
    if (token) requestHeaders.Authorization = `Bearer ${token}`;
  }
  if (idempotencyKey) requestHeaders['Idempotency-Key'] = idempotencyKey;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Unable to connect to the backend. Check that FastAPI is running and the API URL is correct.');
  }

  if (response.status === 401 && auth && retryAuth && path !== '/auth/refresh' && sessionStorage.getItem('refresh_token')) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request(path, { method, body, headers, auth, idempotencyKey, retryAuth: false });
    }
    announceUnauthorized();
  } else if (response.status === 401 && auth && retryAuth && path !== '/auth/refresh' && sessionStorage.getItem('access_token')) {
    announceUnauthorized();
  }

  return parseResponse(response);
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/users/me'),
  wallet: () => request('/wallet'),
  deposit: (amount) => request('/wallet/deposit', { method: 'POST', body: { amount } }),
  withdraw: (amount) => request('/wallet/withdraw', { method: 'POST', body: { amount } }),
  transfer: (payload, idempotencyKey) => request('/transfers', { method: 'POST', body: payload, idempotencyKey }),
  transactions: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
    });
    const suffix = query.toString();
    return request(`/transactions${suffix ? `?${suffix}` : ''}`);
  },
  transaction: (transactionId) => request(`/transactions/${encodeURIComponent(transactionId)}`),
};

export function getApiBaseUrl() {
  return API_BASE_URL;
}
