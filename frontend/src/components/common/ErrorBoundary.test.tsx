import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';

function Boom({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Chart payload was malformed');
  return <p>Recovered content</p>;
}

beforeEach(() => {
  // React logs caught render errors to console.error; silence the noise so a
  // passing test run stays readable.
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ErrorBoundary', () => {
  it('renders its children when nothing throws', () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Recovered content')).toBeInTheDocument();
  });

  it('catches a render crash instead of unmounting the whole tree', () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it('shows the underlying message', () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Chart payload was malformed')).toBeInTheDocument();
  });

  it('names the area that failed, so the user knows what is still usable', () => {
    render(
      <ErrorBoundary area="the analytics charts">
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/in the analytics charts/i)).toBeInTheDocument();
  });

  it('offers a retry that re-renders the subtree', async () => {
    function Wrapper() {
      return (
        <ErrorBoundary>
          <Boom shouldThrow={false} />
        </ErrorBoundary>
      );
    }
    const { rerender } = render(
      <ErrorBoundary>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    rerender(<Wrapper />);

    expect(screen.getByText('Recovered content')).toBeInTheDocument();
  });
});
