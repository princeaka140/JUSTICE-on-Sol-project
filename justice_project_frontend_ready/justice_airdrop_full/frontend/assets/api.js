// Unified frontend API helper
window.BACKEND_URL = window.BACKEND_URL || 'http://127.0.0.1:8000';
window.currentUserId = window.currentUserId || 1; // replace via WebApp auth later

function _authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (window.JWT_TOKEN) headers['Authorization'] = 'Bearer ' + window.JWT_TOKEN;
  if (window.currentUserId) headers['x-user-id'] = String(window.currentUserId);
  return headers;
}

async function apiFetch(path, options = {}) {
  const url = window.BACKEND_URL + path;
  options = Object.assign({ method: 'GET' }, options || {});
  options.headers = Object.assign({}, _authHeaders(), options.headers || {});
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    const err = new Error(`API error ${res.status}: ${text}`);
    err.status = res.status;
    throw err;
  }
  // try to parse json, otherwise return text
  const ct = res.headers.get('content-type') || '';
  if (ct.indexOf('application/json') !== -1) return await res.json();
  return await res.text();
}

async function fetchNotificationCount() {
  try {
    const j = await apiFetch(`/notify/count/${window.currentUserId}`);
    return j.count || 0;
  } catch (e) {
    return 0;
  }
}

async function fetchNotifications(limit = 50) {
  try {
    const j = await apiFetch(`/notify/user/${window.currentUserId}?limit=${limit}`);
    return j.notifications || [];
  } catch (e) {
    return [];
  }
}

async function fetchLogo() {
  try {
    const j = await apiFetch('/api/logo');
    return j.logo_url || null;
  } catch (e) { return null; }
}

async function fetchVideo() {
  try {
    const j = await apiFetch('/api/video');
    return j.video_url || null;
  } catch (e) { return null; }
}

function setCurrentUser(id) {
  window.currentUserId = id;
}

async function updateNotifCountBadge() {
  const el = document.getElementById('notif-count');
  if (!el) return;
  const c = await fetchNotificationCount();
  el.textContent = c || 0;
}

console.log('Unified api helper loaded — backend=', window.BACKEND_URL);
