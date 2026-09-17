/**
 * The single HTTP client.
 *
 * Two behaviours live here so no feature has to reimplement them:
 *
 * 1. **Bearer injection** - the access token from the auth store is attached
 *    to every request.
 * 2. **Transparent refresh** - on a 401 the client refreshes once, replays the
 *    failed request, and queues any other requests that raced into the same
 *    401 so a page issuing four parallel queries triggers one refresh, not
 *    four (which would invalidate each other under token rotation).
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';

import { env } from '@/lib/env';
import type { ApiError, TokenPair } from '@/types/api';

const REQUEST_TIMEOUT_MS = 20_000;
const UNAUTHORIZED = 401;

/** A request config we have already retried once, to stop infinite loops. */
interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

/** Injected by the auth store at startup to avoid a circular import. */
interface TokenBridge {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  onRefreshed: (tokens: TokenPair) => void;
  onRefreshFailed: () => void;
}

let bridge: TokenBridge | null = null;

export function registerTokenBridge(next: TokenBridge): void {
  bridge = next;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${env.apiBaseUrl}/api/v1`,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = bridge?.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- single-flight refresh ---------------------------------------------------

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = bridge?.getRefreshToken();
  if (!refreshToken) return null;

  try {
    // A bare axios call, not `apiClient`: routing this through the instance
    // would re-enter the very interceptor that is handling the 401.
    const { data } = await axios.post<TokenPair>(
      `${env.apiBaseUrl}/api/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: REQUEST_TIMEOUT_MS },
    );
    bridge?.onRefreshed(data);
    return data.access_token;
  } catch {
    bridge?.onRefreshFailed();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const original = error.config as RetriableConfig | undefined;

    // Never try to refresh the auth calls themselves - that would recurse.
    const url = original?.url ?? '';
    const isAuthEndpoint = url.includes('/auth/refresh') || url.includes('/auth/login');
    const isRefreshable =
      error.response?.status === UNAUTHORIZED &&
      original != null &&
      original._retried !== true &&
      !isAuthEndpoint;

    if (!isRefreshable) {
      return Promise.reject(error);
    }

    original._retried = true;
    refreshInFlight ??= refreshAccessToken().finally(() => {
      refreshInFlight = null;
    });

    const token = await refreshInFlight;
    if (!token) {
      return Promise.reject(error);
    }

    original.headers.Authorization = `Bearer ${token}`;
    return apiClient.request(original);
  },
);

// --- error normalisation -----------------------------------------------------

/** A failure surfaced to the UI, already reduced to something displayable. */
export class ApiRequestError extends Error {
  readonly code: string;
  readonly status: number | undefined;
  readonly details: Record<string, unknown> | null;

  constructor(message: string, code: string, status?: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiRequestError';
    this.code = code;
    this.status = status;
    this.details = details ?? null;
  }
}

/**
 * Convert any thrown value into an `ApiRequestError` with a message worth
 * showing a user. Network failures and timeouts get their own wording,
 * because "Request failed with status code undefined" helps nobody.
 */
export function toApiError(error: unknown): ApiRequestError {
  if (error instanceof ApiRequestError) return error;

  if (axios.isAxiosError<ApiError>(error)) {
    if (error.code === 'ECONNABORTED') {
      return new ApiRequestError('The request timed out. Please try again.', 'timeout');
    }
    if (!error.response) {
      return new ApiRequestError(
        'Cannot reach the server. Check your connection and try again.',
        'network_error',
      );
    }
    const body = asApiError(error.response.data);
    return new ApiRequestError(
      body.message ?? error.message,
      body.error ?? 'http_error',
      error.response.status,
      body.details ?? undefined,
    );
  }

  return new ApiRequestError(
    error instanceof Error ? error.message : 'Something went wrong.',
    'unknown_error',
  );
}

/**
 * Read our error envelope out of a response body.
 *
 * A failure can also come from a proxy or a gateway, whose body will not match
 * the envelope at all, so every field is treated as optional.
 */
function asApiError(data: unknown): Partial<ApiError> {
  if (typeof data !== 'object' || data === null) return {};
  const body = data as Record<string, unknown>;
  return {
    ...(typeof body['error'] === 'string' ? { error: body['error'] } : {}),
    ...(typeof body['message'] === 'string' ? { message: body['message'] } : {}),
    ...(typeof body['details'] === 'object' && body['details'] !== null
      ? { details: body['details'] as Record<string, unknown> }
      : {}),
  };
}

/** Perform a request and unwrap the payload, normalising any failure. */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await apiClient.request<T>(config);
    return response.data;
  } catch (error) {
    throw toApiError(error);
  }
}

/**
 * Perform a request that returns 204 No Content.
 *
 * Separate from `request` so no call site has to write `request<void>`, which
 * reads as though a value were expected.
 */
export async function requestNoContent(config: AxiosRequestConfig): Promise<void> {
  await request<unknown>(config);
}
