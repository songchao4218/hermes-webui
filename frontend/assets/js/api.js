/**
 * Hermes WebUI - API Client
 * Centralized API calls with auth token injection.
 */

// API base URL - auto-detect based on how the page is loaded
const API_BASE = (window.location.protocol === 'file:')
    ? 'http://localhost:8080'
    : '';

export function apiUrl(path) {
    return API_BASE + path;
}

// ── Authentication ──────────────────────────────────────────────

export function getAuthToken() {
    return localStorage.getItem('hermes_webui_token') || '';
}

export function setAuthToken(token) {
    localStorage.setItem('hermes_webui_token', token);
}

function authHeaders(extra = {}) {
    const token = getAuthToken();
    const headers = { ...extra };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return headers;
}

/**
 * Wrapper around fetch that injects auth token.
 * Shows auth modal on 401.
 */
export async function apiFetch(url, options = {}) {
    options.headers = authHeaders(options.headers || {});
    const resp = await fetch(url, options);
    if (resp.status === 401) {
        // Dispatch custom event so UI can show auth modal
        window.dispatchEvent(new CustomEvent('auth-required'));
        throw new Error('Authentication required');
    }
    return resp;
}

// ── Typed API Methods ───────────────────────────────────────────

export async function getPersona() {
    const resp = await apiFetch(apiUrl('/api/persona'));
    return resp.json();
}

export async function updatePersona(updates) {
    const resp = await apiFetch(apiUrl('/api/persona'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    return resp.json();
}

export async function uploadAvatar(file, type = 'agent') {
    const formData = new FormData();
    formData.append('file', file);
    if (type === 'user') formData.append('type', 'user');
    const resp = await apiFetch(apiUrl('/api/persona/avatar'), { method: 'POST', body: formData });
    return resp.json();
}

export async function getStatus() {
    const resp = await apiFetch(apiUrl('/api/status'));
    return resp.json();
}

export async function getModels() {
    const resp = await apiFetch(apiUrl('/api/models'));
    return resp.json();
}

export async function getMemories() {
    const resp = await apiFetch(apiUrl('/api/memories'));
    return resp.json();
}

export async function updateMemory(filename, content) {
    const resp = await apiFetch(apiUrl(`/api/memories/${filename}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
    return resp.json();
}

export async function getSkills() {
    const resp = await apiFetch(apiUrl('/api/skills'));
    return resp.json();
}

export async function importSkillZip(file) {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await apiFetch(apiUrl('/api/skills/import'), { method: 'POST', body: formData });
    return resp.json();
}

export async function getSessions() {
    const resp = await apiFetch(apiUrl('/api/sessions'));
    return resp.json();
}

export async function createSession() {
    const resp = await apiFetch(apiUrl('/api/sessions/new'), { method: 'POST' });
    return resp.json();
}

export async function deleteSession(sessionId) {
    const resp = await apiFetch(apiUrl(`/api/sessions/${sessionId}`), { method: 'DELETE' });
    return resp.json();
}

export async function getSessionMessages(sessionId) {
    const resp = await apiFetch(apiUrl(`/api/sessions/${sessionId}/messages`));
    return resp.json();
}

export async function sendChat(message, model, sessionId) {
    return apiFetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, model, session_id: sessionId }),
    });
}

export async function sendChatStream(message, model, sessionId) {
    return apiFetch(apiUrl('/api/chat/stream'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, model, session_id: sessionId }),
    });
}

export async function runAgent(message, sessionId) {
    return apiFetch(apiUrl('/api/agent/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
    });
}

export async function checkUpdate() {
    const resp = await apiFetch(apiUrl('/api/update/check'));
    return resp.json();
}

export async function applyUpdate() {
    return apiFetch(apiUrl('/api/update/apply'), { method: 'POST' });
}
