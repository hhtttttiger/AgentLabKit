import { describe, expect, it } from 'vitest';
import { defaultUsageFilters, usageFiltersFromSearchParams, usageFiltersToSearchParams } from './types';

describe('model monitoring usage filters', () => {
  it('reads filters from search params with sane defaults', () => {
    const filters = usageFiltersFromSearchParams(new URLSearchParams('modelKey=card.alpha&page=2&pageSize=25&fromDate=2026-03-01'));

    expect(filters).toEqual({
      ...defaultUsageFilters,
      modelKey: 'card.alpha',
      fromDate: '2026-03-01',
      page: 2,
      pageSize: 25,
    });
  });

  it('serializes active filters back into search params', () => {
    const params = usageFiltersToSearchParams({
      ...defaultUsageFilters,
      modelKey: 'card.alpha',
      fromDate: '2026-03-01',
      toDate: '2026-03-02',
      page: 3,
    });

    expect(params.toString()).toBe('modelKey=card.alpha&fromDate=2026-03-01&toDate=2026-03-02&page=3');
  });
});
