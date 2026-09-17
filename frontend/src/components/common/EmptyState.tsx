import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

/**
 * The "nothing here yet" surface.
 *
 * Every empty list uses this rather than rendering blank space, so a new
 * account sees an explanation and a next step instead of an empty page that
 * looks broken.
 */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-14 text-center',
        className,
      )}
    >
      <div className="rounded-full border border-surface-800 bg-surface-850 p-3">
        <Icon className="h-6 w-6 text-content-muted" aria-hidden />
      </div>
      <div className="max-w-sm space-y-1">
        <h3 className="text-sm font-semibold text-content-primary">{title}</h3>
        <p className="text-xs leading-relaxed text-content-muted">{description}</p>
      </div>
      {action != null && <div className="pt-1">{action}</div>}
    </div>
  );
}
