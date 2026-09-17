/** Auth mutations and the session bootstrap hook. */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { authApi } from '@/features/auth/api/authApi';
import { useAuthStore } from '@/features/auth/store/authStore';
import type { LoginPayload, RegisterPayload } from '@/types/api';

/**
 * Restore the persisted session on first mount and revalidate it.
 *
 * Reading `localStorage` alone would happily "restore" a session whose account
 * has since been deleted or deactivated, so a `/auth/me` call confirms the
 * token is still good and refreshes the cached profile.
 */
export function useSessionBootstrap(): { isHydrating: boolean } {
  const hydrate = useAuthStore((state) => state.hydrate);
  const isHydrating = useAuthStore((state) => state.isHydrating);
  const accessToken = useAuthStore((state) => state.accessToken);
  const setUser = useAuthStore((state) => state.setUser);
  const signOut = useAuthStore((state) => state.signOut);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isHydrating || !accessToken) return undefined;

    let cancelled = false;
    authApi
      .me()
      .then((user) => {
        if (!cancelled) setUser(user);
      })
      .catch(() => {
        // The interceptor already tried to refresh; reaching here means the
        // whole session is dead.
        if (!cancelled) signOut();
      });

    return () => {
      cancelled = true;
    };
    // Runs once per hydrated session, not on every token rotation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHydrating]);

  return { isHydrating };
}

/** Sign in with email and password. */
export function useLogin() {
  const signIn = useAuthStore((state) => state.signIn);

  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (data) => {
      signIn(data.user, data.tokens);
    },
  });
}

/** Create an account and sign in. */
export function useRegister() {
  const signIn = useAuthStore((state) => state.signIn);

  return useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
    onSuccess: (data) => {
      signIn(data.user, data.tokens);
    },
  });
}

/** Sign out, revoking the refresh token server-side and clearing caches. */
export function useLogout() {
  const queryClient = useQueryClient();
  const signOut = useAuthStore((state) => state.signOut);
  const refreshToken = useAuthStore((state) => state.refreshToken);

  return useMutation({
    mutationFn: async (): Promise<void> => {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // A failed revoke must not trap the user in a signed-in UI; the local
        // session is cleared either way and the token expires on its own.
      }
    },
    onSettled: () => {
      signOut();
      // Clearing rather than invalidating: the next user on this browser must
      // not briefly see the previous user's cached projects.
      queryClient.clear();
    },
  });
}
