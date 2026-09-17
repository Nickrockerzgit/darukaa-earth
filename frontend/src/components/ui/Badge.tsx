import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';
import type { ProjectStatus, ProjectType } from '@/types/api';

type Tone = 'neutral' | 'carbon' | 'biodiversity' | 'mixed' | 'success' | 'warning' | 'muted';

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-800 text-content-secondary border-surface-700',
  carbon: 'bg-metric-carbon/12 text-metric-carbon border-metric-carbon/30',
  biodiversity: 'bg-metric-biodiversity/12 text-metric-biodiversity border-metric-biodiversity/30',
  mixed: 'bg-brand-400/12 text-brand-300 border-brand-400/30',
  success: 'bg-positive/12 text-positive border-positive/30',
  warning: 'bg-warning/12 text-warning border-warning/30',
  muted: 'bg-surface-850 text-content-muted border-surface-800',
};

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const PROJECT_TYPE_TONE: Record<ProjectType, Tone> = {
  carbon: 'carbon',
  biodiversity: 'biodiversity',
  mixed: 'mixed',
};

const PROJECT_TYPE_LABEL: Record<ProjectType, string> = {
  carbon: 'Carbon',
  biodiversity: 'Biodiversity',
  mixed: 'Mixed',
};

/** Project type badge, colour-matched to the map fill for the same type. */
export function ProjectTypeBadge({ type }: { type: ProjectType }) {
  return <Badge tone={PROJECT_TYPE_TONE[type]}>{PROJECT_TYPE_LABEL[type]}</Badge>;
}

const STATUS_TONE: Record<ProjectStatus, Tone> = {
  draft: 'muted',
  active: 'success',
  archived: 'warning',
};

const STATUS_LABEL: Record<ProjectStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  archived: 'Archived',
};

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}
