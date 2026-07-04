import { afterEach, describe, expect, it, vi } from 'vitest';
import { createFolder, listFolders, moveFolder } from './api';

describe('knowledge base folder api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('lists folders from the knowledge base folder endpoint', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        success: true,
        msg: 'ok',
        data: [{ id: 'folder-1', knowledgeBaseId: 'kb-1', parentFolderId: null, name: 'Docs', sortOrder: 0, createdAtUtc: '2026-05-08T00:00:00Z' }],
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );

    const result = await listFolders('kb-1');

    expect(result[0]?.id).toBe('folder-1');
    expect(fetchSpy).toHaveBeenCalledWith('/api/knowledge-bases/kb-1/folders', expect.any(Object));
  });

  it('posts folder create and move payloads to the folder endpoints', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify({
          success: true,
          msg: 'ok',
          data: { id: 'folder-1', knowledgeBaseId: 'kb-1', parentFolderId: null, name: 'Docs', sortOrder: 0, createdAtUtc: '2026-05-08T00:00:00Z' },
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await createFolder('kb-1', { name: 'Docs', parentFolderId: null });
    await moveFolder('kb-1', 'folder-1', { targetParentFolderId: 'parent-1' });

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      '/api/knowledge-bases/kb-1/folders',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Docs', parentFolderId: null }),
      }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      '/api/knowledge-bases/kb-1/folders/folder-1/move',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ targetParentFolderId: 'parent-1' }),
      }),
    );
  });
});
