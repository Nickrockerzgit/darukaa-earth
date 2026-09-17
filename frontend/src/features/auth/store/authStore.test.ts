import { beforeEach, describe, expect, it } from 'vitest';

import { useAuthStore } from '@/features/auth/store/authStore';
import type { TokenPair, User } from '@/types/api';

const USER: User = {
  id: 'user-1',
  email: 'admin@darukaa.earth',
  full_name: 'Demo Admin',
  role: 'admin',
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
};

const TOKENS: TokenPair = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'bearer',
  expires_in: 900,
};

const STORAGE_KEY = 'darukaa.auth';

beforeEach(() => {
  window.localStorage.clear();
  useAuthStore.setState({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isHydrating: true,
  });
});

describe('signIn', () => {
  it('stores the session in memory', () => {
    useAuthStore.getState().signIn(USER, TOKENS);

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe(USER.email);
    expect(state.accessToken).toBe('access-1');
  });

  it('persists the session so a refresh does not sign the user out', () => {
    useAuthStore.getState().signIn(USER, TOKENS);
    expect(window.localStorage.getItem(STORAGE_KEY)).toContain('refresh-1');
  });
});

describe('signOut', () => {
  it('clears memory and storage', () => {
    useAuthStore.getState().signIn(USER, TOKENS);
    useAuthStore.getState().signOut();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe('setTokens', () => {
  it('rotates the stored tokens while keeping the user', () => {
    useAuthStore.getState().signIn(USER, TOKENS);
    useAuthStore.getState().setTokens({ ...TOKENS, access_token: 'a2', refresh_token: 'r2' });

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('a2');
    expect(state.refreshToken).toBe('r2');
    expect(state.user?.id).toBe(USER.id);
    expect(window.localStorage.getItem(STORAGE_KEY)).toContain('r2');
  });
});

describe('hydrate', () => {
  it('restores a persisted session', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'a', refreshToken: 'r', user: USER }),
    );
    useAuthStore.getState().hydrate();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isHydrating).toBe(false);
    expect(state.user?.email).toBe(USER.email);
  });

  it('finishes hydrating with no session when storage is empty', () => {
    useAuthStore.getState().hydrate();

    expect(useAuthStore.getState().isHydrating).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('ignores corrupt storage instead of crashing the app', () => {
    window.localStorage.setItem(STORAGE_KEY, 'not json');
    useAuthStore.getState().hydrate();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().isHydrating).toBe(false);
  });

  it('ignores a partial session', () => {
    // A half-written record must not produce a "signed in" state with no token.
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ accessToken: 'a' }));
    useAuthStore.getState().hydrate();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
