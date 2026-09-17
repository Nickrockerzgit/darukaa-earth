import { Leaf } from 'lucide-react';
import type { ReactNode } from 'react';

/**
 * Shell for the sign-in and sign-up screens.
 *
 * Two panes: the form on the left, a product statement on the right. The right
 * pane collapses below `lg`, so on a phone the form gets the whole viewport.
 */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="grid h-full lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5">
            <div className="rounded-xl border border-brand-500/30 bg-brand-500/12 p-2">
              <Leaf className="h-5 w-5 text-brand-400" aria-hidden />
            </div>
            <span className="text-lg font-semibold tracking-tight text-content-primary">
              Darukaa<span className="text-brand-400">.Earth</span>
            </span>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">{title}</h1>
          <p className="mt-1.5 text-sm text-content-muted">{subtitle}</p>

          <div className="mt-8">{children}</div>
          <div className="mt-6 text-sm text-content-muted">{footer}</div>
        </div>
      </div>

      <aside className="relative hidden overflow-hidden border-l border-surface-800 bg-gradient-to-br from-surface-900 to-surface-950 lg:block">
        {/* Decorative contour rings, suggesting a topographic map. */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 30% 30%, transparent 0 18%, currentColor 18% 18.4%, transparent 18.4%), radial-gradient(circle at 30% 30%, transparent 0 30%, currentColor 30% 30.4%, transparent 30.4%), radial-gradient(circle at 70% 65%, transparent 0 22%, currentColor 22% 22.4%, transparent 22.4%)',
            color: 'var(--color-brand-400)',
          }}
        />
        <div className="relative flex h-full flex-col justify-center px-14">
          <p className="text-xs font-semibold tracking-[0.18em] text-brand-400 uppercase">
            Measurement, reporting, verification
          </p>
          <h2 className="mt-4 max-w-md text-3xl leading-tight font-semibold tracking-tight text-content-primary">
            Every hectare, measured over time.
          </h2>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-content-secondary">
            Draw a project boundary on the map and Darukaa.Earth tracks carbon sequestration, canopy
            cover and biodiversity across it, month by month, so a claim is always traceable to a
            polygon and a date.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-6">
            {[
              ['PostGIS', 'Geospatial core'],
              ['6 metrics', 'Per site, monthly'],
              ['Mapbox GL', 'Draw and inspect'],
            ].map(([value, label]) => (
              <div key={label}>
                <dt className="text-sm font-semibold text-content-primary">{value}</dt>
                <dd className="mt-0.5 text-xs text-content-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </aside>
    </div>
  );
}
