/**
 * Thin fetch wrapper around the PayerGuard backend.
 *
 * The one piece of real design here is `NotComputedError`. Several backend
 * endpoints answer 404 for a legitimate, expected reason -- the pipeline
 * stage that produces their artifact has not been run yet (`/anomaly/results`
 * before a benchmark, `/quality/results` before a validation run). That is
 * not a failure and it is not "no data"; it is a distinct state the UI has to
 * report honestly rather than rendering a zero. Callers get a typed error so
 * they can say "not computed yet" instead of inventing a value.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/** The requested artifact does not exist yet because its pipeline stage has not run. */
export class NotComputedError extends Error {
  constructor(public readonly path: string, public readonly detail: string) {
    super(detail || `Not computed yet: ${path}`);
    this.name = 'NotComputedError';
  }
}

/** Any other non-2xx response. */
export class ApiError extends Error {
  constructor(
    public readonly path: string,
    public readonly status: number,
    public readonly detail: string
  ) {
    super(`${status} ${path}: ${detail}`);
    this.name = 'ApiError';
  }
}

async function readDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    return JSON.stringify(body);
  } catch {
    return response.statusText;
  }
}

/** An explicitly empty Content-Type means "let the browser decide" (multipart). */
function buildHeaders(overrides?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((overrides as Record<string, string>) ?? {}),
  };
  if (headers['Content-Type'] === '') delete headers['Content-Type'];
  return headers;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: buildHeaders(init?.headers),
    });
  } catch (cause) {
    // Network-level failure: backend down, wrong port, CORS preflight refused.
    throw new ApiError(path, 0, `Cannot reach the backend at ${BASE_URL}.`);
  }

  if (response.status === 404) {
    throw new NotComputedError(path, await readDetail(response));
  }
  if (!response.ok) {
    throw new ApiError(path, response.status, await readDetail(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const query = params
    ? Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';
  return request<T>(query ? `${path}?${query}` : path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/**
 * Multipart upload. `Content-Type` is deliberately not set: the browser has
 * to write it itself so it can include the multipart boundary, and setting
 * it here would produce a header with no boundary and a 422 from FastAPI.
 */
export function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append('file', file);
  return request<T>(path, { method: 'POST', body: form, headers: { 'Content-Type': '' } });
}

export { BASE_URL };
