import { afterEach, describe, expect, it, vi } from 'vitest';
import { createQaPair, importQaPairs, listDocuments, moveDocument, uploadDocument } from './api';

describe('knowledge base document api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('includes folder_id in the document list query string', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        success: true,
        msg: 'ok',
        data: { items: [], totalCount: 0, page: 1, pageSize: 20 },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );

    await listDocuments('kb-1', { page: 1, pageSize: 20, folder_id: 'folder-1' });

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/knowledge-bases/kb-1/documents?page=1&pageSize=20&folder_id=folder-1',
      expect.any(Object),
    );
  });

  it('posts targetFolderId when moving a document', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));

    await moveDocument('kb-1', 'doc-1', 'folder-9');

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/knowledge-bases/kb-1/documents/doc-1/move',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ targetFolderId: 'folder-9' }),
      }),
    );
  });

  it('includes folderId in upload form data', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 202 }));
    const file = new File(['hello'], 'guide.md', { type: 'text/markdown' });

    await uploadDocument('kb-1', file, 'folder-1');

    const [, init] = fetchSpy.mock.calls[0] ?? [];
    const body = init?.body as FormData;

    expect(body.get('folderId')).toBe('folder-1');
  });

  it('posts folderId when creating a qa pair', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 202 }));

    await createQaPair('kb-1', { question: 'Q', answer: 'A', folderId: 'folder-2' });

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/knowledge-bases/kb-1/documents/qa',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ question: 'Q', answer: 'A', folderId: 'folder-2' }),
      }),
    );
  });

  it('includes folderId in import form data', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 200 }));
    const file = new File(['q,a'], 'qa.csv', { type: 'text/csv' });

    await importQaPairs('kb-1', file, 'folder-3');

    const [, init] = fetchSpy.mock.calls[0] ?? [];
    const body = init?.body as FormData;

    expect(body.get('folderId')).toBe('folder-3');
  });
});
