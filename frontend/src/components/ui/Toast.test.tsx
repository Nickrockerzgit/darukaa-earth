import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import { Toaster } from '@/components/ui/Toast';
import { toast, useToastStore } from '@/lib/toast';

beforeEach(() => {
  useToastStore.setState({ toasts: [] });
});

describe('Toaster', () => {
  it('renders nothing when there are no toasts', () => {
    render(<Toaster />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders a pushed toast', () => {
    render(<Toaster />);
    act(() => {
      toast.success('Project created.');
    });

    expect(screen.getByText('Project created.')).toBeInTheDocument();
  });

  it('announces politely, so it does not interrupt a screen reader mid-sentence', () => {
    const { container } = render(<Toaster />);
    expect(container.querySelector('[aria-live="polite"]')).toBeInTheDocument();
  });

  it('stacks multiple toasts', () => {
    render(<Toaster />);
    act(() => {
      toast.success('One');
      toast.error('Two');
    });

    expect(screen.getAllByRole('status')).toHaveLength(2);
  });

  it('can be dismissed by the user', async () => {
    render(<Toaster />);
    act(() => {
      toast.info('Dismiss me');
    });

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }));
    expect(screen.queryByText('Dismiss me')).not.toBeInTheDocument();
  });

  it('styles an error differently from a success', () => {
    render(<Toaster />);
    act(() => {
      toast.error('Failed');
    });

    expect(screen.getByRole('status').className).toContain('text-negative');
  });
});
