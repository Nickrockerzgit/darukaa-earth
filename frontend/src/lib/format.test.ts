import { describe, expect, it } from 'vitest';

import {
  formatArea,
  formatChange,
  formatDate,
  formatMetricValue,
  formatMonth,
  humanise,
  toTimestamp,
} from '@/lib/format';

describe('formatMetricValue', () => {
  it('keeps two decimals for small values, where precision is the signal', () => {
    // NDVI moving 0.52 -> 0.54 is meaningful; rounding to 1 would erase it.
    expect(formatMetricValue(0.5234)).toBe('0.52');
  });

  it('drops noise decimals on larger values', () => {
    expect(formatMetricValue(1234.567)).toBe('1,234.6');
  });

  it('switches to compact notation above ten thousand', () => {
    // A KPI tile has no room for "12,431.57".
    expect(formatMetricValue(12_431.57)).toBe('12.4K');
  });

  it('appends a word unit with a space', () => {
    expect(formatMetricValue(42, 'tCO2e')).toBe('42 tCO2e');
  });

  it('hugs a percent sign to its number', () => {
    expect(formatMetricValue(42, '%')).toBe('42%');
  });

  it('handles negatives', () => {
    expect(formatMetricValue(-3.5)).toBe('-3.50');
  });

  it('handles zero', () => {
    expect(formatMetricValue(0)).toBe('0.00');
  });
});

describe('formatArea', () => {
  it('reports hectares below the threshold', () => {
    expect(formatArea(120.45)).toBe('120.5 ha');
  });

  it('promotes very large areas to square kilometres', () => {
    expect(formatArea(50_000)).toBe('500 km²');
  });

  it('handles zero', () => {
    expect(formatArea(0)).toBe('0 ha');
  });
});

describe('formatChange', () => {
  it('prefixes a gain with a plus sign', () => {
    expect(formatChange(12.34)).toBe('+12.3%');
  });

  it('keeps the minus sign on a loss', () => {
    expect(formatChange(-5)).toBe('-5.0%');
  });

  it('renders an em dash when there is no baseline', () => {
    // Showing "0%" here would claim a stability the data does not support.
    expect(formatChange(null)).toBe('—');
  });

  it('renders an em dash for NaN', () => {
    expect(formatChange(Number.NaN)).toBe('—');
  });
});

describe('date formatting', () => {
  it('formats an ISO date', () => {
    expect(formatDate('2025-03-12')).toBe('12 Mar 2025');
  });

  it('formats a month bucket', () => {
    expect(formatMonth('2025-03-01')).toBe('Mar 2025');
  });

  it('returns the input unchanged when it cannot be parsed', () => {
    // A malformed date must not blank out a whole chart axis.
    expect(formatDate('not-a-date')).toBe('not-a-date');
  });

  it('converts to epoch milliseconds for Highcharts', () => {
    expect(toTimestamp('2025-01-01')).toBe(new Date('2025-01-01T00:00:00').getTime());
  });
});

describe('humanise', () => {
  it('turns a metric key into a readable label', () => {
    expect(humanise('carbon_stock_tco2e')).toBe('Carbon stock tco2e');
  });

  it('handles an empty string', () => {
    expect(humanise('')).toBe('');
  });
});
