/** Vitest global setup: DOM matchers plus jsdom gaps the app relies on. */

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, vi } from 'vitest';

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

beforeAll(() => {
  // jsdom implements neither of these, and both are used by components under
  // test: `<dialog>` in Modal, and ResizeObserver inside Highcharts.
  const dialogProto = HTMLDialogElement.prototype as unknown as Record<string, unknown>;
  if (typeof dialogProto['showModal'] !== 'function') {
    dialogProto['showModal'] = function showModal(this: HTMLDialogElement) {
      this.open = true;
    };
    dialogProto['close'] = function close(this: HTMLDialogElement) {
      this.open = false;
    };
  }

  const globals = globalThis as unknown as Record<string, unknown>;
  globals['ResizeObserver'] ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

  const win = window as unknown as Record<string, unknown>;
  win['matchMedia'] ??= (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
});
