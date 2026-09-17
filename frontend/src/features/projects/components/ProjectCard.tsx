import { ArrowUpRight, Layers, Ruler } from 'lucide-react';
import { Link } from 'react-router-dom';

import { ProjectStatusBadge, ProjectTypeBadge } from '@/components/ui/Badge';
import { formatArea, formatDate } from '@/lib/format';
import type { ProjectWithStats } from '@/types/api';

export function ProjectCard({ project }: { project: ProjectWithStats }) {
  return (
    <Link
      to={`/projects/${project.id}`}
      className="panel group flex flex-col gap-3 p-5 transition-colors hover:border-brand-500/50"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="line-clamp-1 text-sm font-semibold text-content-primary">{project.name}</h3>
        <ArrowUpRight className="h-4 w-4 shrink-0 text-content-muted transition-colors group-hover:text-brand-400" />
      </div>

      <p className="line-clamp-2 min-h-[2rem] text-xs leading-relaxed text-content-muted">
        {project.description ?? 'No description provided.'}
      </p>

      <div className="flex flex-wrap gap-1.5">
        <ProjectTypeBadge type={project.project_type} />
        <ProjectStatusBadge status={project.status} />
      </div>

      <dl className="grid grid-cols-2 gap-3 border-t border-surface-800 pt-3">
        <div className="flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-content-muted" aria-hidden />
          <div>
            <dt className="text-[10px] tracking-wide text-content-muted uppercase">Sites</dt>
            <dd className="text-sm font-medium text-content-primary tabular-nums">
              {project.site_count}
            </dd>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Ruler className="h-3.5 w-3.5 text-content-muted" aria-hidden />
          <div>
            <dt className="text-[10px] tracking-wide text-content-muted uppercase">Area</dt>
            <dd className="text-sm font-medium text-content-primary tabular-nums">
              {formatArea(project.total_area_hectares)}
            </dd>
          </div>
        </div>
      </dl>

      {project.start_date != null && (
        <p className="text-[11px] text-content-muted">Started {formatDate(project.start_date)}</p>
      )}
    </Link>
  );
}
