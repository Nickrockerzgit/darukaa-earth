import type { Feature, Polygon } from 'geojson';
import { Check, PencilRuler, X } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { useCreateSite } from '@/features/sites/hooks/useSites';

const MIN_NAME_LENGTH = 2;

export interface AddSitePanelProps {
  projectId: string;
  isDrawing: boolean;
  drawnFeature: Feature<Polygon> | null;
  onStartDrawing: () => void;
  onCancel: () => void;
  onCreated: () => void;
}

/**
 * The draw-then-name flow for adding a site.
 *
 * Deliberately two steps: the user draws the shape first and only then names
 * it. Asking for a name up front would leave a half-filled form sitting on
 * screen during the part of the interaction that needs the whole map.
 */
export function AddSitePanel({
  projectId,
  isDrawing,
  drawnFeature,
  onStartDrawing,
  onCancel,
  onCreated,
}: AddSitePanelProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const createSite = useCreateSite(projectId);

  const reset = () => {
    setName('');
    setDescription('');
  };

  const handleCancel = () => {
    reset();
    onCancel();
  };

  const handleSave = () => {
    if (!drawnFeature) return;
    createSite.mutate(
      {
        name: name.trim(),
        description: description.trim() ? description.trim() : null,
        geometry: drawnFeature.geometry,
      },
      {
        onSuccess: () => {
          reset();
          onCreated();
        },
      },
    );
  };

  if (!isDrawing && !drawnFeature) {
    return (
      <Button
        variant="secondary"
        size="sm"
        className="w-full justify-center"
        leftIcon={<PencilRuler className="h-3.5 w-3.5" />}
        onClick={onStartDrawing}
      >
        Draw a new site
      </Button>
    );
  }

  if (isDrawing && !drawnFeature) {
    return (
      <div className="space-y-2 rounded-lg border border-brand-500/40 bg-brand-500/8 px-3 py-2.5">
        <p className="text-xs font-medium text-brand-300">Drawing mode</p>
        <p className="text-xs leading-relaxed text-content-muted">
          Click on the map to place each corner, then click the first point again (or double-click)
          to close the shape.
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center"
          leftIcon={<X className="h-3.5 w-3.5" />}
          onClick={handleCancel}
        >
          Cancel
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-surface-700 bg-surface-850 p-3">
      <p className="text-xs font-medium text-content-secondary">Name this site</p>
      <Input
        value={name}
        onChange={(event) => {
          setName(event.target.value);
        }}
        placeholder="Gosaba Block North"
        aria-label="Site name"
        autoFocus
      />
      <Textarea
        value={description}
        onChange={(event) => {
          setDescription(event.target.value);
        }}
        placeholder="Optional notes"
        aria-label="Site description"
        className="min-h-16"
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          className="flex-1 justify-center"
          leftIcon={<Check className="h-3.5 w-3.5" />}
          disabled={name.trim().length < MIN_NAME_LENGTH}
          isLoading={createSite.isPending}
          onClick={handleSave}
        >
          Save site
        </Button>
        <Button variant="ghost" size="sm" onClick={handleCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
