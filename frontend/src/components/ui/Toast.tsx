import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

import { cn } from '@/lib/cn';
import { useToastStore, type ToastTone } from '@/lib/toast';

const TONE_STYLES: Record<ToastTone, { className: string; Icon: typeof Info }> = {
  success: { className: 'border-positive/40 text-positive', Icon: CheckCircle2 },
  error: { className: 'border-negative/40 text-negative', Icon: AlertCircle },
  info: { className: 'border-info/40 text-info', Icon: Info },
};

/** Renders the toast stack. Mounted once, near the app root. */
export function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div
      // `polite` so a background success does not interrupt what a screen
      // reader is currently announcing.
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed right-4 bottom-4 z-[100] flex w-full max-w-sm flex-col gap-2"
    >
      {toasts.map((item) => {
        const { className, Icon } = TONE_STYLES[item.tone];
        return (
          <div
            key={item.id}
            role="status"
            className={cn(
              'panel pointer-events-auto flex items-start gap-3 border px-4 py-3 text-sm',
              className,
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <p className="flex-1 text-content-primary">{item.message}</p>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => {
                dismiss(item.id);
              }}
              className="text-content-muted transition-colors hover:text-content-primary"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
