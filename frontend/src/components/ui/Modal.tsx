import { X } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '@/lib/cn';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'md' | 'lg';
}

/**
 * A modal dialog.
 *
 * Built on the native `<dialog>` element so focus trapping, the top layer and
 * inert background content come from the platform rather than from a
 * hand-rolled focus manager that will eventually get it wrong.
 */
export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    // Escape closes the dialog natively; intercept it so React state stays in
    // sync rather than leaving `isOpen` true over a closed dialog.
    const handleCancel = (event: Event) => {
      event.preventDefault();
      onClose();
    };
    dialog.addEventListener('cancel', handleCancel);
    return () => {
      dialog.removeEventListener('cancel', handleCancel);
    };
  }, [onClose]);

  return createPortal(
    <dialog
      ref={dialogRef}
      aria-labelledby="modal-title"
      className={cn(
        'panel m-auto w-[calc(100vw-2rem)] p-0 text-content-primary backdrop:bg-black/60',
        size === 'lg' ? 'max-w-3xl' : 'max-w-lg',
      )}
      // A click on the backdrop lands on the dialog element itself.
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
    >
      <div className="flex items-start justify-between gap-4 border-b border-surface-800 px-5 py-4">
        <div>
          <h2 id="modal-title" className="text-base font-semibold">
            {title}
          </h2>
          {description != null && (
            <p className="mt-0.5 text-xs text-content-muted">{description}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close dialog"
          className="rounded-md p-1 text-content-muted transition-colors hover:bg-surface-800 hover:text-content-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>

      {footer != null && (
        <div className="flex justify-end gap-2 border-t border-surface-800 px-5 py-4">{footer}</div>
      )}
    </dialog>,
    document.body,
  );
}
