import { QueryCache, QueryClient } from '@tanstack/react-query';

import { ApiRequestError } from '@/lib/apiClient';
import { toast } from '@/lib/toast';

const HTTP_UNAUTHORIZED = 401;
const HTTP_CLIENT_ERROR_FLOOR = 400;
const HTTP_SERVER_ERROR_FLOOR = 500;
const MAX_RETRIES = 2;

/**
 * The app's single query client.
 *
 * Two policies worth calling out:
 *
 * - **No retries on 4xx.** A 404 or a validation error will fail identically
 *   three times; retrying only delays the error the user needs to see.
 * - **One global error toast.** Queries report failures centrally so no
 *   feature has to remember an `onError`; mutations keep their own, because
 *   their messages are action-specific.
 */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // A background refetch failing should not interrupt the user; only the
      // first load of a given query surfaces a toast.
      if (query.state.data !== undefined) return;
      if (error instanceof ApiRequestError && error.status === HTTP_UNAUTHORIZED) return;
      toast.error(error instanceof Error ? error.message : 'Request failed.');
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiRequestError) {
          const status = error.status ?? 0;
          if (status >= HTTP_CLIENT_ERROR_FLOOR && status < HTTP_SERVER_ERROR_FLOOR) {
            return false;
          }
        }
        return failureCount < MAX_RETRIES;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
