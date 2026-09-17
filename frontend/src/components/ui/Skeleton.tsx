import type { CSSProperties } from 'react';

import { cn } from '@/lib/cn';

/**
 * A shimmering placeholder.
 *
 * Skeletons rather than spinners: they preserve the page's layout, so content
 * does not jump when it arrives, and they communicate what is loading.
 */
export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      style={style}
      className={cn('animate-pulse rounded-md bg-surface-800', className)}
    />
  );
}

/** Placeholder matching the shape of a project card. */
export function CardSkeleton() {
  return (
    <div className="panel space-y-3 p-5">
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
    </div>
  );
}

/** Placeholder matching the shape of a chart panel. */
export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div className="panel p-5">
      <Skeleton className="mb-4 h-4 w-40" />
      <Skeleton className="w-full" style={{ height }} />
    </div>
  );
}
