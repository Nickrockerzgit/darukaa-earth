import { Leaf, LayoutGrid, LogOut, Map as MapIcon, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { useLogout } from '@/features/auth/hooks/useAuth';
import { useAuthStore } from '@/features/auth/store/authStore';
import { cn } from '@/lib/cn';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Projects', icon: LayoutGrid },
  { to: '/map', label: 'Map', icon: MapIcon },
] as const;

/**
 * The authenticated application frame.
 *
 * A fixed sidebar on desktop, a slide-over on mobile. The main region is a
 * `min-h-0` flex child so the full-bleed map page can own the viewport height
 * without the page itself scrolling.
 */
export function AppShell() {
  const [isNavOpen, setIsNavOpen] = useState(false);
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();

  const closeNav = () => {
    setIsNavOpen(false);
  };

  return (
    <div className="flex h-full">
      {isNavOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={closeNav}
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-surface-800 bg-surface-900',
          'transition-transform duration-200 lg:static lg:translate-x-0',
          isNavOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-surface-800 px-4">
          <div className="flex items-center gap-2">
            <div className="rounded-lg border border-brand-500/30 bg-brand-500/12 p-1.5">
              <Leaf className="h-4 w-4 text-brand-400" aria-hidden />
            </div>
            <span className="text-sm font-semibold tracking-tight text-content-primary">
              Darukaa<span className="text-brand-400">.Earth</span>
            </span>
          </div>
          <button
            type="button"
            onClick={closeNav}
            aria-label="Close navigation"
            className="text-content-muted hover:text-content-primary lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-3" aria-label="Main">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={closeNav}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-brand-500/12 font-medium text-brand-300'
                    : 'text-content-secondary hover:bg-surface-800 hover:text-content-primary',
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-3 border-t border-surface-800 p-3">
          <div className="px-1">
            <p className="truncate text-xs font-medium text-content-primary">
              {user?.full_name ?? 'Signed in'}
            </p>
            <p className="truncate text-xs text-content-muted">{user?.email}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            isLoading={logout.isPending}
            leftIcon={<LogOut className="h-3.5 w-3.5" />}
            onClick={() => {
              logout.mutate();
            }}
          >
            Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-surface-800 px-4 lg:hidden">
          <button
            type="button"
            onClick={() => {
              setIsNavOpen(true);
            }}
            aria-label="Open navigation"
            className="text-content-secondary hover:text-content-primary"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-content-primary">Darukaa.Earth</span>
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
