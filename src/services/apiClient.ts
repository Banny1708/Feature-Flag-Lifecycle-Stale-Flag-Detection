/**
 * API Client for the FastAPI backend.
 * All requests go to the real backend (VITE_API_URL, default http://127.0.0.1:8000).
 * Failures throw — callers render loading/error states instead of fake data.
 */

export const API_BASE_URL: string =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_URL ??
  'http://127.0.0.1:8000';

function buildUrl(path: string, params?: Record<string, string>): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') url.searchParams.set(k, v);
    }
  }
  return url.toString();
}

async function parseError(res: Response, path: string): Promise<Error> {
  let detail = `Backend ${res.status} for ${path}`;
  try {
    const err = (await res.json()) as { detail?: string };
    if (err.detail) detail = err.detail;
  } catch {
    /* keep default */
  }
  return new Error(detail);
}

/** GET JSON from the backend. Throws on network/HTTP error. */
export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    throw await parseError(res, path);
  }
  return (await res.json()) as T;
}

async function apiWrite<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    throw await parseError(res, path);
  }
  return (await res.json()) as T;
}

/** POST JSON to the backend. Throws on network/HTTP error. */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiWrite<T>('POST', path, body);
}

/** PATCH JSON to the backend. Throws on network/HTTP error. */
export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return apiWrite<T>('PATCH', path, body);
}

/** PUT JSON to the backend. Throws on network/HTTP error. */
export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return apiWrite<T>('PUT', path, body);
}
