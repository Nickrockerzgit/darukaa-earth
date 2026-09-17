import { AlertTriangle } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

import { Button } from '@/components/ui/Button';

interface Props {
  children: ReactNode;
  /** Optional label naming the area that failed, e.g. "the analytics panel". */
  area?: string;
}

interface State {
  error: Error | null;
}

/**
 * Catches render-time crashes.
 *
 * Without this, one bad chart payload unmounts the entire React tree and the
 * user is left staring at a white page. Class component because React still
 * has no hook equivalent for error boundaries.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // In production this is where a Sentry call would go.
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  private readonly handleReset = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    const { error } = this.state;
    const { children, area } = this.props;

    if (!error) return children;

    return (
      <div className="panel flex flex-col items-center gap-3 px-6 py-12 text-center">
        <AlertTriangle className="h-6 w-6 text-warning" aria-hidden />
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-content-primary">
            Something went wrong{area != null ? ` in ${area}` : ''}
          </h3>
          <p className="max-w-sm text-xs text-content-muted">{error.message}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={this.handleReset}>
          Try again
        </Button>
      </div>
    );
  }
}
