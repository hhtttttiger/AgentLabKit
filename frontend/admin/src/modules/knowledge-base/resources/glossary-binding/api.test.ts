import { afterEach, describe, expect, it, vi } from 'vitest';
import { getKnowledgeBaseGlossaryBinding } from './api';

describe('glossary binding api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('reads the backend knowledgeBaseId field from the binding endpoint', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        success: true,
        msg: 'ok',
        data: {
          knowledgeBaseId: 'kb-1',
          categoryIds: ['cat-1'],
          categories: [],
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );

    const result = await getKnowledgeBaseGlossaryBinding('kb-1');

    expect(result.knowledgeBaseId).toBe('kb-1');
    expect(result.categoryIds).toEqual(['cat-1']);
  });
});
