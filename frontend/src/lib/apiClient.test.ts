import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';

import { apiClient, ApiRequestError, toApiError } from '@/lib/apiClient';

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const error = new AxiosError('Request failed');
  error.response = {
    status,
    statusText: '',
    data,
    headers: {},
    config: { headers: new AxiosHeaders() },
  };
  return error;
}

describe('toApiError', () => {
  it('passes an ApiRequestError through unchanged', () => {
    const original = new ApiRequestError('boom', 'custom_code', 418);
    expect(toApiError(original)).toBe(original);
  });

  it('extracts our error envelope', () => {
    const error = toApiError(
      axiosErrorWith(404, { error: 'not_found', message: 'Project not found.' }),
    );

    expect(error.code).toBe('not_found');
    expect(error.message).toBe('Project not found.');
    expect(error.status).toBe(404);
  });

  it('keeps the details payload', () => {
    const error = toApiError(
      axiosErrorWith(422, {
        error: 'validation_error',
        message: 'Invalid.',
        details: { field: 'name' },
      }),
    );
    expect(error.details).toEqual({ field: 'name' });
  });

  it('falls back gracefully when the body is not our envelope', () => {
    // A gateway or proxy error will not have the envelope at all.
    const error = toApiError(axiosErrorWith(502, '<html>Bad Gateway</html>'));

    expect(error.code).toBe('http_error');
    expect(error.status).toBe(502);
    expect(error.message).toBe('Request failed');
  });

  it('gives a timeout its own message', () => {
    const timeout = new AxiosError('timeout of 20000ms exceeded', 'ECONNABORTED');
    const error = toApiError(timeout);

    expect(error.code).toBe('timeout');
    expect(error.message).toMatch(/timed out/i);
  });

  it('gives an unreachable server its own message', () => {
    // "Request failed with status code undefined" helps nobody.
    const offline = new AxiosError('Network Error');
    const error = toApiError(offline);

    expect(error.code).toBe('network_error');
    expect(error.message).toMatch(/cannot reach the server/i);
  });

  it('wraps a plain Error', () => {
    const error = toApiError(new Error('something odd'));

    expect(error.code).toBe('unknown_error');
    expect(error.message).toBe('something odd');
  });

  it('wraps a non-Error throw', () => {
    const error = toApiError('a bare string');
    expect(error.code).toBe('unknown_error');
    expect(error.message).toBe('Something went wrong.');
  });
});

describe('apiClient', () => {
  it('targets the versioned API prefix', () => {
    expect(apiClient.defaults.baseURL).toMatch(/\/api\/v1$/);
  });

  it('sets a request timeout so a hung request cannot block the UI forever', () => {
    expect(apiClient.defaults.timeout).toBeGreaterThan(0);
  });
});
