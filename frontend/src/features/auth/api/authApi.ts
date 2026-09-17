/** HTTP calls for the auth endpoints. */

import { request } from '@/lib/apiClient';
import type { AuthResponse, LoginPayload, RegisterPayload, TokenPair, User } from '@/types/api';

export const authApi = {
  register: (payload: RegisterPayload) =>
    request<AuthResponse>({ method: 'POST', url: '/auth/register', data: payload }),

  login: (payload: LoginPayload) =>
    request<AuthResponse>({ method: 'POST', url: '/auth/login', data: payload }),

  refresh: (refreshToken: string) =>
    request<TokenPair>({
      method: 'POST',
      url: '/auth/refresh',
      data: { refresh_token: refreshToken },
    }),

  logout: (refreshToken: string | null) =>
    request<{ message: string }>({
      method: 'POST',
      url: '/auth/logout',
      data: refreshToken ? { refresh_token: refreshToken } : null,
    }),

  me: () => request<User>({ method: 'GET', url: '/auth/me' }),
};
