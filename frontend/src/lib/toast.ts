/**
 * Toast state and the imperative API for raising one.
 *
 * Kept out of the component file so non-component code - mutation `onError`
 * callbacks, the query client's global handler - can report failures without
 * being rewritten as components, and so the component file exports only
 * components (which is what React Fast Refresh needs).
 */

import { create } from 'zustand';

export type ToastTone = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  tone: ToastTone;
  message: string;
}

interface ToastState {
  toasts: Toast[];
  push: (tone: ToastTone, message: string) => void;
  dismiss: (id: string) => void;
}

const AUTO_DISMISS_MS = 5000;

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  push: (tone, message) => {
    const id = crypto.randomUUID();
    set((state) => ({ toasts: [...state.toasts, { id, tone, message }] }));
    window.setTimeout(() => {
      get().dismiss(id);
    }, AUTO_DISMISS_MS);
  },
  dismiss: (id) => {
    set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) }));
  },
}));

export const toast = {
  success: (message: string) => {
    useToastStore.getState().push('success', message);
  },
  error: (message: string) => {
    useToastStore.getState().push('error', message);
  },
  info: (message: string) => {
    useToastStore.getState().push('info', message);
  },
};
