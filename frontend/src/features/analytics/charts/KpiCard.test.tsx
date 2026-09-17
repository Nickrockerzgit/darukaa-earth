import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { KpiCard } from '@/features/analytics/charts/KpiCard';
import type { MetricSnapshot } from '@/types/api';

function snapshot(overrides: Partial<MetricSnapshot> = {}): MetricSnapshot {
  return {
    metric_key: 'carbon_sequestered_tco2e',
    label: 'Carbon Sequestered',
    unit: 'tCO2e',
    category: 'carbon',
    latest_value: 1250.5,
    latest_date: '2025-09-01',
    previous_value: 1100,
    change_pct: 13.68,
    ...overrides,
  };
}

describe('KpiCard', () => {
  it('shows the metric label and formatted value', () => {
    render(<KpiCard snapshot={snapshot()} />);

    expect(screen.getByText('Carbon Sequestered')).toBeInTheDocument();
    expect(screen.getByText('1,250.5 tCO2e')).toBeInTheDocument();
  });

  it('shows the date the value is as of', () => {
    render(<KpiCard snapshot={snapshot()} />);
    expect(screen.getByText(/as of 1 Sep 2025/)).toBeInTheDocument();
  });

  it('renders a positive change with a plus sign', () => {
    render(<KpiCard snapshot={snapshot()} />);
    expect(screen.getByText('+13.7%')).toBeInTheDocument();
  });

  it('renders a negative change', () => {
    render(<KpiCard snapshot={snapshot({ change_pct: -8.2 })} />);
    expect(screen.getByText('-8.2%')).toBeInTheDocument();
  });

  it('renders an em dash when there is no baseline', () => {
    render(<KpiCard snapshot={snapshot({ previous_value: null, change_pct: null })} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('formats a percentage metric without a stray space', () => {
    render(
      <KpiCard
        snapshot={snapshot({
          metric_key: 'canopy_cover_pct',
          label: 'Canopy Cover',
          unit: '%',
          category: 'vegetation',
          latest_value: 61.4,
        })}
      />,
    );
    expect(screen.getByText('61.4%')).toBeInTheDocument();
  });
});
