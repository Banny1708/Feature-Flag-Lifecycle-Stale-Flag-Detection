/**
 * API Client abstraction.
 * Talks to the FastAPI backend when reachable (VITE_API_URL),
 * otherwise callers fall back to local mock data so the UI keeps working.
 */

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

const SIMULATED_DELAY_MS = 100;

export const API_BASE_URL: string =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_URL ??
  'http://127.0.0.1:8000';

export async function simulateFetch<T>(data: T, delayMs: number = SIMULATED_DELAY_MS): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(JSON.parse(JSON.stringify(data)));
    }, delayMs);
  });
}

/** GET JSON from the backend. Throws on network/HTTP error so callers can fall back to mocks. */
export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Backend ${res.status} for ${path}`);
  }
  return (await res.json()) as T;
}

/** POST JSON to the backend. Throws on network/HTTP error. */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Backend ${res.status} for ${path}`;
    try {
      const err = (await res.json()) as { detail?: string };
      if (err.detail) detail = err.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

/**
 * Try the backend first; fall back to the provided mock loader when the
 * backend is unreachable (dev without backend, offline demo, etc.).
 */
export async function backendFirst<T>(fn: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch {
    return await fallback();
  }
}
