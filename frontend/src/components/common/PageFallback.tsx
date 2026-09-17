import { Loader2 } from 'lucide-react';

/** Suspense fallback for lazily-loaded routes. */
export function PageFallback() {
  return (
    <div className="flex h-full items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-brand-500" aria-label="Loading page" />
    </div>
  );
}
