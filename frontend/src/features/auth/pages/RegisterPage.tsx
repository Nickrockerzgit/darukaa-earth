import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Lock, Mail, User } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { useRegister } from '@/features/auth/hooks/useAuth';
import { registerSchema, type RegisterFormValues } from '@/features/auth/schemas';

export function RegisterPage() {
  const navigate = useNavigate();
  const signUp = useRegister();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    // Validate as the user corrects a field, not on every keystroke from the
    // start: errors appearing before the first attempt feel accusatory.
    mode: 'onTouched',
    defaultValues: { email: '', fullName: '', password: '' },
  });

  const onSubmit = handleSubmit((values) => {
    signUp.mutate(
      {
        email: values.email,
        password: values.password,
        ...(values.fullName ? { full_name: values.fullName } : {}),
      },
      {
        onSuccess: () => {
          navigate('/dashboard', { replace: true });
        },
      },
    );
  });

  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start mapping and measuring your restoration sites."
      footer={
        <>
          Already registered?{' '}
          <Link to="/login" className="font-medium text-brand-400 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {signUp.isError && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-negative/40 bg-negative/10 px-3 py-2.5 text-xs text-negative"
          >
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
            <span>{signUp.error.message}</span>
          </div>
        )}

        <Input
          {...register('fullName')}
          label="Full name"
          placeholder="Ada Lovelace"
          autoComplete="name"
          leftIcon={<User className="h-4 w-4" />}
          error={errors.fullName?.message}
        />
        <Input
          {...register('email')}
          type="email"
          label="Email"
          placeholder="you@organisation.org"
          autoComplete="email"
          leftIcon={<Mail className="h-4 w-4" />}
          error={errors.email?.message}
        />
        <Input
          {...register('password')}
          type="password"
          label="Password"
          placeholder="At least 10 characters"
          autoComplete="new-password"
          leftIcon={<Lock className="h-4 w-4" />}
          error={errors.password?.message}
          hint="At least 10 characters, with an uppercase letter, a lowercase letter and a digit."
        />

        <Button
          type="submit"
          size="lg"
          className="w-full justify-center"
          isLoading={signUp.isPending}
        >
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
