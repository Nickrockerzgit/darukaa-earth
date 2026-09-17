import { act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { toast, useToastStore } from '@/lib/toast';

beforeEach(() => {
  vi.useFakeTimers();
  useToastStore.setState({ toasts: [] });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('toast', () => {
  it('pushes a success toast', () => {
    toast.success('Project created.');

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({ tone: 'success', message: 'Project created.' });
  });

  it('pushes an error toast', () => {
    toast.error('Something failed.');
    expect(useToastStore.getState().toasts[0]?.tone).toBe('error');
  });

  it('pushes an info toast', () => {
    toast.info('Heads up.');
    expect(useToastStore.getState().toasts[0]?.tone).toBe('info');
  });

  it('stacks several toasts', () => {
    toast.success('One');
    toast.error('Two');
    expect(useToastStore.getState().toasts).toHaveLength(2);
  });

  it('gives each toast a unique id, so React keys stay stable', () => {
    toast.success('One');
    toast.success('One');

    const [first, second] = useToastStore.getState().toasts;
    expect(first?.id).not.toBe(second?.id);
  });

  it('dismisses itself after the timeout', () => {
    toast.success('Transient');
    expect(useToastStore.getState().toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it('dismisses only the requested toast', () => {
    toast.success('Keep');
    toast.error('Drop');
    const target = useToastStore.getState().toasts[1];

    act(() => {
      useToastStore.getState().dismiss(target!.id);
    });

    const remaining = useToastStore.getState().toasts;
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.message).toBe('Keep');
  });
});
