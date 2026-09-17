import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { useCreateProject } from '@/features/projects/hooks/useProjects';
import type { ProjectStatus, ProjectType } from '@/types/api';

const schema = z.object({
  name: z.string().min(2, 'Use at least 2 characters').max(160, 'Use at most 160 characters'),
  description: z.string().max(4000, 'Use at most 4000 characters').optional(),
  project_type: z.enum(['carbon', 'biodiversity', 'mixed']),
  status: z.enum(['draft', 'active', 'archived']),
  start_date: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const TYPE_OPTIONS: { value: ProjectType; label: string }[] = [
  { value: 'carbon', label: 'Carbon' },
  { value: 'biodiversity', label: 'Biodiversity' },
  { value: 'mixed', label: 'Mixed' },
];

const STATUS_OPTIONS: { value: ProjectStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
];

export function CreateProjectModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const createProject = useCreateProject();

  const { register, handleSubmit, reset, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      description: '',
      project_type: 'carbon',
      status: 'active',
      start_date: '',
    },
  });

  // Reset when the dialog opens, so a cancelled draft does not reappear.
  useEffect(() => {
    if (isOpen) reset();
  }, [isOpen, reset]);

  const onSubmit = handleSubmit((values) => {
    createProject.mutate(
      {
        name: values.name,
        description: values.description ?? null,
        project_type: values.project_type,
        status: values.status,
        start_date: values.start_date ? values.start_date : null,
      },
      { onSuccess: onClose },
    );
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New project"
      description="A project groups the sites you monitor together."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" form="create-project-form" isLoading={createProject.isPending}>
            Create project
          </Button>
        </>
      }
    >
      <form id="create-project-form" onSubmit={onSubmit} noValidate className="space-y-4">
        <Input
          {...register('name')}
          label="Project name"
          placeholder="Sundarbans Mangrove Restoration"
          error={formState.errors.name?.message}
          autoFocus
        />
        <Textarea
          {...register('description')}
          label="Description"
          placeholder="What is being restored, and how is it measured?"
          error={formState.errors.description?.message}
        />
        <div className="grid grid-cols-2 gap-3">
          <Select {...register('project_type')} label="Type" options={TYPE_OPTIONS} />
          <Select {...register('status')} label="Status" options={STATUS_OPTIONS} />
        </div>
        <Input {...register('start_date')} type="date" label="Start date (optional)" />
      </form>
    </Modal>
  );
}
