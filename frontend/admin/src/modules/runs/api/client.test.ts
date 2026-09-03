import { describe, expect, it, vi } from 'vitest';
import { apiRequest } from '@/shared/api/client';
import { listRuns } from './client';

vi.mock('@/shared/api/client', () => ({
  apiRequest: vi.fn(),
}));

describe('listRuns', () => {
  it('passes the requested page to the durable Runs endpoint', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ items: [], total: 41 });

    await listRuns(20, 20);

    expect(apiRequest).toHaveBeenCalledWith('/api/runs?limit=20&offset=20');
  });
});
