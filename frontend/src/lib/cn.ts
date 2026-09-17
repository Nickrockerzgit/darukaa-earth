import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge class names, letting later Tailwind utilities win over earlier ones.
 *
 * Without `twMerge`, `cn('p-2', 'p-4')` would emit both and leave the winner up
 * to stylesheet order - which is exactly the bug that makes component variant
 * props unreliable.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
