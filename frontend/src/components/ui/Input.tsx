import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: ReactNode;
}

/**
 * A labelled text input.
 *
 * Label, hint and error are wired to the control with htmlFor,
 * aria-describedby and aria-invalid, so a screen reader announces the
 * validation message instead of leaving it as unattached red text.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, label, error, hint, leftIcon, id, ...props },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = `${inputId}-message`;
  const hasMessage = Boolean(error ?? hint);

  return (
    <div className="flex w-full flex-col gap-1.5">
      {label != null && (
        <label htmlFor={inputId} className="text-sm font-medium text-content-secondary">
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon != null && (
          <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-content-muted">
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error != null}
          aria-describedby={hasMessage ? messageId : undefined}
          className={cn(
            'h-10 w-full rounded-lg border bg-surface-950 px-3 text-sm text-content-primary',
            'placeholder:text-content-muted',
            'transition-colors focus:ring-2 focus:ring-brand-500/40 focus:outline-none',
            error != null
              ? 'border-negative focus:border-negative'
              : 'border-surface-700 focus:border-brand-500',
            leftIcon != null && 'pl-9',
            className,
          )}
          {...props}
        />
      </div>
      {hasMessage && (
        <p
          id={messageId}
          className={cn('text-xs', error != null ? 'text-negative' : 'text-content-muted')}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
});
