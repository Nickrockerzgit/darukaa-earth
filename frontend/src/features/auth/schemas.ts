/**
 * Form validation schemas.
 *
 * These mirror the backend's Pydantic rules so a user sees the problem while
 * typing rather than after a round trip. The server still enforces the same
 * rules - this is a UX layer, not a security boundary.
 */

import { z } from 'zod';

const MIN_PASSWORD_LENGTH = 10;
const MAX_PASSWORD_BYTES = 72;

export const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

export const registerSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  fullName: z
    .string()
    .max(160, 'Name must be 160 characters or fewer')
    .optional()
    .or(z.literal('')),
  password: z
    .string()
    .min(MIN_PASSWORD_LENGTH, `Use at least ${MIN_PASSWORD_LENGTH} characters`)
    // bcrypt truncates past 72 bytes, so the backend rejects longer inputs.
    .max(MAX_PASSWORD_BYTES, `Use at most ${MAX_PASSWORD_BYTES} characters`)
    .regex(/[a-z]/, 'Include a lowercase letter')
    .regex(/[A-Z]/, 'Include an uppercase letter')
    .regex(/\d/, 'Include a digit'),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
