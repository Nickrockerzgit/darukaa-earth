import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Lock, Mail } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { useLogin } from '@/features/auth/hooks/useAuth';
import { loginSchema, type LoginFormValues } from '@/features/auth/schemas';

interface LocationState {
  from?: { pathname?: string };
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = handleSubmit((values) => {
    login.mutate(values, {
      onSuccess: () => {
        // Return the user to whatever they were trying to reach.
        const state = location.state as LocationState | null;
        navigate(state?.from?.pathname ?? '/dashboard', { replace: true });
      },
    });
  });

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Access your carbon and biodiversity project dashboard."
      footer={
        <>
          No account yet?{' '}
          <Link to="/register" className="font-medium text-brand-400 hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {login.isError && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-negative/40 bg-negative/10 px-3 py-2.5 text-xs text-negative"
          >
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
            <span>{login.error.message}</span>
          </div>
        )}

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
          placeholder="Your password"
          autoComplete="current-password"
          leftIcon={<Lock className="h-4 w-4" />}
          error={errors.password?.message}
        />

        <Button
          type="submit"
          size="lg"
          className="w-full justify-center"
          isLoading={login.isPending}
        >
          Sign in
        </Button>
      </form>

      <p className="mt-6 rounded-lg border border-surface-800 bg-surface-900 px-3 py-2.5 text-xs leading-relaxed text-content-muted">
        <span className="font-medium text-content-secondary">Demo account</span>
        <br />
        admin@darukaa.earth / DarukaaDemo123!
      </p>
    </AuthLayout>
  );
}
