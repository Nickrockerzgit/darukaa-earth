import { FolderPlus, Plus, Search } from 'lucide-react';
import { useState } from 'react';

import { EmptyState } from '@/components/common/EmptyState';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { CardSkeleton } from '@/components/ui/Skeleton';
import { CreateProjectModal } from '@/features/projects/components/CreateProjectModal';
import { ProjectCard } from '@/features/projects/components/ProjectCard';
import { useProjects } from '@/features/projects/hooks/useProjects';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import type { ProjectStatus } from '@/types/api';

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'draft', label: 'Draft' },
  { value: 'archived', label: 'Archived' },
];

const PAGE_SIZE = 12;

export function DashboardPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<ProjectStatus | ''>('');
  const [page, setPage] = useState(1);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Debounced so typing does not fire a request per keystroke.
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useProjects({
    page,
    size: PAGE_SIZE,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(status ? { status } : {}),
  });

  const projects = query.data?.items ?? [];
  const isFiltered = Boolean(debouncedSearch || status);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-content-primary">Projects</h1>
            <p className="mt-1 text-sm text-content-muted">
              {query.data
                ? `${query.data.total} project${query.data.total === 1 ? '' : 's'}`
                : 'Loading your projects…'}
            </p>
          </div>
          <Button
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => {
              setIsCreateOpen(true);
            }}
          >
            New project
          </Button>
        </header>

        <div className="mb-6 flex flex-wrap gap-3">
          <div className="min-w-56 flex-1">
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search projects by name"
              leftIcon={<Search className="h-4 w-4" />}
              aria-label="Search projects"
            />
          </div>
          <div className="w-44">
            <Select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as ProjectStatus | '');
                setPage(1);
              }}
              options={STATUS_FILTER_OPTIONS}
              aria-label="Filter by status"
            />
          </div>
        </div>

        {query.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <CardSkeleton key={index} />
            ))}
          </div>
        ) : query.isError ? (
          <div className="panel">
            <EmptyState
              icon={FolderPlus}
              title="Could not load projects"
              description={query.error.message}
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    void query.refetch();
                  }}
                >
                  Retry
                </Button>
              }
            />
          </div>
        ) : projects.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={FolderPlus}
              title={isFiltered ? 'No matching projects' : 'No projects yet'}
              description={
                isFiltered
                  ? 'Try a different search term or clear the status filter.'
                  : 'Create your first project, then draw its sites on the map to start tracking carbon and biodiversity over time.'
              }
              action={
                isFiltered ? (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSearch('');
                      setStatus('');
                    }}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <Button
                    leftIcon={<Plus className="h-4 w-4" />}
                    onClick={() => {
                      setIsCreateOpen(true);
                    }}
                  >
                    Create a project
                  </Button>
                )
              }
            />
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>

            {(query.data?.pages ?? 1) > 1 && (
              <nav aria-label="Pagination" className="mt-6 flex items-center justify-center gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => {
                    setPage((current) => current - 1);
                  }}
                >
                  Previous
                </Button>
                <span className="text-xs text-content-muted tabular-nums">
                  Page {page} of {query.data?.pages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= (query.data?.pages ?? 1)}
                  onClick={() => {
                    setPage((current) => current + 1);
                  }}
                >
                  Next
                </Button>
              </nav>
            )}
          </>
        )}
      </div>

      <CreateProjectModal
        isOpen={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
        }}
      />
    </div>
  );
}
