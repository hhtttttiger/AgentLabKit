import { describe, expect, it, vi, afterEach } from 'vitest';
import { apiRequest } from './client';
import { ApiError } from './errors';

describe('apiRequest', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns envelope data on success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ success: true, msg: 'ok', data: { value: 1 } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(apiRequest<{ value: number }>('/api/demo')).resolves.toEqual({ value: 1 });
  });

  it('throws api error on failed response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ success: false, msg: 'Boom', data: null }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(apiRequest('/api/demo')).rejects.toBeInstanceOf(ApiError);
  });

  it('returns undefined on no-content success response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, {
        status: 204,
      }),
    );

    await expect(apiRequest<void>('/api/demo', { method: 'DELETE' })).resolves.toBeUndefined();
  });

  it('sends form data without forcing json content-type', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ success: true, msg: 'ok', data: { uploaded: true } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const form = new FormData();
    form.append('file', new Blob(['demo']), 'demo.txt');

    await expect(
      apiRequest<{ uploaded: boolean }>('/api/upload', { method: 'POST', formBody: form }),
    ).resolves.toEqual({ uploaded: true });

    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.body).toBe(form);
    expect((init?.headers as Record<string, string>)['Content-Type']).toBeUndefined();
  });
});
