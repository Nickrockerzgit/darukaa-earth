/**
 * Authentication state.
 *
 * Tokens live in `localStorage` so a page refresh does not sign the user out.
 * That is a deliberate trade-off, recorded in ADR-0006: an httpOnly refresh
 * cookie is stronger against XSS, but needs a shared parent domain between the
 * Vercel frontend and the Render API, which this deployment does not have.
 * The mitigations are a 15-minute access token and one-use refresh rotation.
 */

import { create } from 'zustand';

import { registerTokenBridge } from '@/lib/apiClient';
import type { TokenPair, User } from '@/types/api';

const STORAGE_KEY = 'darukaa.auth';

interface PersistedAuth {
  accessToken: string;
  refreshToken: string;
  user: User;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  /** True until the stored session has been read back on first load. */
  isHydrating: boolean;
  isAuthenticated: boolean;

  signIn: (user: User, tokens: TokenPair) => void;
  signOut: () => void;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: User) => void;
  hydrate: () => void;
}

function readPersisted(): PersistedAuth | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PersistedAuth>;
    if (!parsed.accessToken || !parsed.refreshToken || !parsed.user) return null;
    return parsed as PersistedAuth;
  } catch {
    // Corrupt or unavailable storage (private mode, quota) must not brick the
    // app - treat it as "signed out".
    return null;
  }
}

function writePersisted(value: PersistedAuth | null): void {
  try {
    if (value === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    }
  } catch {
    // Storage being unavailable degrades persistence, not the session.
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isHydrating: true,
  isAuthenticated: false,

  signIn: (user, tokens) => {
    writePersisted({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user,
    });
    set({
      user,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      isAuthenticated: true,
      isHydrating: false,
    });
  },

  signOut: () => {
    writePersisted(null);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isHydrating: false,
    });
  },

  setTokens: (tokens) => {
    const { user } = get();
    if (user) {
      writePersisted({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        user,
      });
    }
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },

  setUser: (user) => {
    const { accessToken, refreshToken } = get();
    if (accessToken && refreshToken) {
      writePersisted({ accessToken, refreshToken, user });
    }
    set({ user });
  },

  hydrate: () => {
    const persisted = readPersisted();
    set(
      persisted
        ? {
            user: persisted.user,
            accessToken: persisted.accessToken,
            refreshToken: persisted.refreshToken,
            isAuthenticated: true,
            isHydrating: false,
          }
        : { isHydrating: false },
    );
  },
}));

/**
 * Connect the store to the HTTP client.
 *
 * The bridge exists so `apiClient` can read tokens without importing the
 * store, which would create a cycle (store -> apiClient -> store).
 */
registerTokenBridge({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getRefreshToken: () => useAuthStore.getState().refreshToken,
  onRefreshed: (tokens) => {
    useAuthStore.getState().setTokens(tokens);
  },
  onRefreshFailed: () => {
    useAuthStore.getState().signOut();
  },
});
