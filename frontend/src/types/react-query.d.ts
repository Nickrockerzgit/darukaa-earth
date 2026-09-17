import type { ApiRequestError } from '@/lib/apiClient';

/**
 * Tell TanStack Query that every error it surfaces is an `ApiRequestError`.
 *
 * Without this, each hook has to repeat `<TData, ApiRequestError>` just to get
 * a typed `error`, and one forgotten generic silently degrades a component to
 * the base `Error` type. Registering it once makes the correct type the
 * default everywhere.
 */
declare module '@tanstack/react-query' {
  interface Register {
    defaultError: ApiRequestError;
  }
}
