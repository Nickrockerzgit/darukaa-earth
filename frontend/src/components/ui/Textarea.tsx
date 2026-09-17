import { forwardRef, useId, type TextareaHTMLAttributes } from 'react';

import { cn } from '@/lib/cn';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

/** A labelled multi-line input, matching the accessibility wiring in Input. */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, label, error, id, ...props },
  ref,
) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  const messageId = `${textareaId}-message`;

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label != null && (
        <label htmlFor={textareaId} className="text-sm font-medium text-content-secondary">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        aria-invalid={error != null}
        aria-describedby={error != null ? messageId : undefined}
        className={cn(
          'min-h-20 w-full resize-y rounded-lg border px-3 py-2 text-sm',
          'bg-surface-950 text-content-primary placeholder:text-content-muted',
          'transition-colors focus:ring-2 focus:ring-brand-500/40 focus:outline-none',
          error != null
            ? 'border-negative focus:border-negative'
            : 'border-surface-700 focus:border-brand-500',
          className,
        )}
        {...props}
      />
      {error != null && (
        <p id={messageId} className="text-xs text-negative">
          {error}
        </p>
      )}
    </div>
  );
});
