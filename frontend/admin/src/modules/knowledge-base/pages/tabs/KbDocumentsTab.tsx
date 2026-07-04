import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Plus, RefreshCw, RotateCw, Trash2, Upload } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { ToolbarButton } from '@/shared/ui/ToolbarButton';
import { useToast } from '@/shared/ui/Toast';
import { Pagination } from '@/shared/ui/Pagination';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { KbDocumentView, KbFolderView } from '../../lib/contracts';
import { DocumentDetailDrawer } from '../../resources/document/components/DocumentDetailDrawer';
import { QaImportDrawer } from '../../resources/document/components/QaImportDrawer';
import { QaPairEditor } from '../../resources/document/components/QaPairEditor';
import { useDocumentDetail, useDocumentList, useDocumentMutations } from '../../resources/document/hooks';
import { defaultDocumentListFilters } from '../../resources/document/types';
import { FolderCreateModal } from '../../resources/folder/components/FolderCreateModal';
import { useFolderList, useFolderMutations } from '../../resources/folder/hooks';
import { KbFolderBreadcrumb, type BreadcrumbItem } from './components/KbFolderBreadcrumb';
import { KbUnifiedList, type UnifiedListItem } from './components/KbUnifiedList';

export function KbDocumentsTab() {
  const { kbId = '' } = useParams<{ kbId: string }>();
  const { t } = useTranslation('common');
  const { toast } = useToast();
  useAdminLocale();

  const [filters, setFilters] = useState(defaultDocumentListFilters);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([{ id: null, name: '全部' }]);
  const [qaEditorOpen, setQaEditorOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState<KbDocumentView | null>(null);
  const [detailDocId, setDetailDocId] = useState<string | null>(null);
  const [deletingDoc, setDeletingDoc] = useState<KbDocumentView | null>(null);
  const [deletingFolder, setDeletingFolder] = useState<KbFolderView | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [batchActionPending, setBatchActionPending] = useState<'reindex' | 'delete' | null>(null);
  const [importQaOpen, setImportQaOpen] = useState(false);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const currentFolderIdRef = useRef<string | null>(null);

  const currentFolderId = breadcrumb[breadcrumb.length - 1]?.id ?? null;
  currentFolderIdRef.current = currentFolderId;
  const queryFilters = useMemo(
    () => ({ ...filters, folderId: currentFolderId === null ? '0' : currentFolderId }),
    [currentFolderId, filters],
  );

  const listQuery = useDocumentList(kbId, queryFilters);
  const detailQuery = useDocumentDetail(kbId, detailDocId ?? '');
  const { data: allFolders = [] } = useFolderList(kbId);
  const documentMutations = useDocumentMutations(kbId);
  const folderMutations = useFolderMutations(kbId);

  const documents = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);
  const totalCount = listQuery.data?.totalCount ?? 0;
  const detailDoc = detailDocId
    ? documents.find((doc) => doc.id === detailDocId) ?? detailQuery.data ?? null
    : null;

  const currentFolderChildren = useMemo(
    () => allFolders
      .filter((folder) => folder.parentFolderId === currentFolderId)
      .sort((left, right) => left.sortOrder - right.sortOrder || left.name.localeCompare(right.name)),
    [allFolders, currentFolderId],
  );

  const unifiedItems = useMemo<UnifiedListItem[]>(
    () => [
      ...currentFolderChildren.map((folder) => ({ type: 'folder', data: folder }) satisfies UnifiedListItem),
      ...documents.map((doc) => ({ type: 'document', data: doc }) satisfies UnifiedListItem),
    ],
    [currentFolderChildren, documents],
  );

  useEffect(() => {
    setSelectedIds((prev) => {
      const visibleIds = new Set(documents.map((doc) => doc.id));
      const next = new Set(Array.from(prev).filter((id) => visibleIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [documents]);

  useEffect(() => {
    const next: BreadcrumbItem[] = [{ id: null, name: '全部' }];

    if (currentFolderId !== null) {
      const folderMap = new Map(allFolders.map((folder) => [folder.id, folder]));
      const chain: BreadcrumbItem[] = [];
      let cursorId: string | null = currentFolderId;

      while (cursorId) {
        const folder = folderMap.get(cursorId);
        if (!folder) {
          break;
        }

        chain.unshift({ id: folder.id, name: folder.name });
        cursorId = folder.parentFolderId;
      }

      if (chain.length > 0) {
        next.push(...chain);
      }
    }

    setBreadcrumb((prev) => {
      if (prev.length === next.length && prev.every((item, index) => item.id === next[index]?.id && item.name === next[index]?.name)) {
        return prev;
      }

      return next;
    });
  }, [allFolders, currentFolderId]);

  useEffect(() => {
    if (detailDocId && !documents.some((doc) => doc.id === detailDocId)) {
      setDetailDocId(null);
    }
  }, [detailDocId, documents]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => (
      prev.size === documents.length ? new Set() : new Set(documents.map((doc) => doc.id))
    ));
  }, [documents]);

  const clearSelection = useCallback(() => setSelectedIds(new Set()), []);

  const navigateIntoFolder = useCallback((folder: KbFolderView) => {
    setBreadcrumb((prev) => [...prev, { id: folder.id, name: folder.name }]);
    setFilters((prev) => ({ ...prev, page: 1 }));
  }, []);

  const navigateTo = useCallback((item: BreadcrumbItem) => {
    setBreadcrumb((prev) => {
      const index = prev.findIndex((candidate) => candidate.id === item.id);
      return index >= 0 ? prev.slice(0, index + 1) : prev;
    });
    setFilters((prev) => ({ ...prev, page: 1 }));
  }, []);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) {
      return;
    }

    for (const file of Array.from(files)) {
      documentMutations.upload.mutate({ file, folderId: currentFolderIdRef.current }, {
        onSuccess: () => toast(t('toast.uploadSuccess')),
        onError: () => toast(t('toast.uploadFailed'), 'error'),
      });
    }

    event.target.value = '';
  }, [documentMutations.upload, toast]);

  const handleReindex = useCallback((docId: string) => {
    documentMutations.reindex.mutate(docId, {
      onSuccess: () => toast(t('toast.reindexSubmitted')),
      onError: () => toast(t('toast.operationFailed'), 'error'),
    });
  }, [documentMutations.reindex, toast]);

  const handleDocumentMove = useCallback(async (docId: string, targetFolderId: string | null) => {
    await documentMutations.moveDoc.mutateAsync({ docId, targetFolderId });
    toast(t('toast.updated'));
  }, [documentMutations.moveDoc, toast]);

  const runBatchMutation = useCallback(
    async (
      action: 'reindex' | 'delete',
      mutation: (docId: string) => Promise<unknown>,
      successMessage: (count: number) => string,
      partialMessage: (successCount: number, failedCount: number) => string,
      failureMessage: (count: number) => string,
    ) => {
      const ids = Array.from(selectedIds);
      if (ids.length === 0) {
        return;
      }

      setBatchActionPending(action);
      try {
        const results = await Promise.allSettled(ids.map((id) => mutation(id)));
        const failedIds = ids.filter((_, index) => results[index]?.status === 'rejected');
        const successCount = ids.length - failedIds.length;

        setSelectedIds(new Set(failedIds));

        if (failedIds.length === 0) {
          toast(successMessage(successCount));
          return;
        }

        if (successCount > 0) {
          toast(partialMessage(successCount, failedIds.length), 'info');
          return;
        }

        toast(failureMessage(failedIds.length), 'error');
      } finally {
        setBatchActionPending(null);
      }
    },
    [selectedIds, toast],
  );

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept=".pdf,.txt,.md,.json,.html"
        onChange={handleFileSelect}
      />

      <ManagementListFrame
        refreshing={listQuery.isFetching}
        pagination={(
          <Pagination
            page={filters.page}
            pageSize={filters.pageSize}
            totalCount={totalCount}
            onChange={(page) => setFilters((prev) => ({ ...prev, page }))}
            onPageSizeChange={(pageSize) => setFilters((prev) => ({ ...prev, page: 1, pageSize }))}
          />
        )}
        toolbar={(
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              {selectedIds.size > 0 && (
                <div className="flex items-center gap-3 rounded-[2px] border border-primary/20 bg-primary-subtle p-3 text-sm">
                  <span className="text-text">
                    已选择 <strong>{selectedIds.size}</strong> 个文档
                  </span>
                  <Button
                    variant="secondary"
                    disabled={batchActionPending !== null}
                    onClick={() =>
                      runBatchMutation(
                        'reindex',
                        (id) => documentMutations.reindex.mutateAsync(id),
                        (count) => `已提交 ${count} 个文档的重新索引`,
                        (successCount, failedCount) => `已提交 ${successCount} 个，仍有 ${failedCount} 个重新索引失败`,
                        (count) => `${count} 个文档重新索引失败`,
                      )
                    }
                  >
                    <RotateCw size={14} />
                    批量重索引
                  </Button>
                  <Button
                    variant="danger"
                    disabled={batchActionPending !== null}
                    onClick={() => setBatchDeleteOpen(true)}
                  >
                    <Trash2 size={14} />
                    批量删除
                  </Button>
                  <Button variant="ghost" disabled={batchActionPending !== null} onClick={clearSelection}>
                    取消选择
                  </Button>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2">
                <ToolbarButton variant="secondary" onClick={() => setCreateFolderOpen(true)}>
                  <Plus size={14} />
                  新建文件夹
                </ToolbarButton>
                <ToolbarButton variant="secondary" onClick={() => fileInputRef.current?.click()}>
                  <Upload size={14} />
                  上传文件
                </ToolbarButton>
                <ToolbarButton variant="secondary" onClick={() => setImportQaOpen(true)}>
                  <Upload size={14} />
                  导入 QA
                </ToolbarButton>
                <ToolbarButton variant="primary" onClick={() => setQaEditorOpen(true)}>
                  <Plus size={14} />
                  创建 QA 对
                </ToolbarButton>
                <Button
                  variant="secondary"
                  onClick={() => listQuery.refetch()}
                  disabled={listQuery.isFetching}
                >
                  <RefreshCw size={14} className={listQuery.isFetching ? 'animate-spin' : undefined} />
                  刷新
                </Button>
              </div>
            </div>

            <KbFolderBreadcrumb path={breadcrumb} onNavigate={navigateTo} />
          </div>
        )}
      >
        {documentMutations.upload.isPending ? (
          <div className="mb-4 rounded-[2px] border border-primary/20 bg-primary-subtle p-3 text-sm text-primary">
            正在上传文件...
          </div>
        ) : null}

        <KbUnifiedList
          kbId={kbId}
          items={unifiedItems}
          onFolderClick={navigateIntoFolder}
          onDocumentClick={(doc) => setDetailDocId(doc.id)}
          onDocumentEdit={(doc) => setEditingDoc(doc)}
          onDocumentReindex={(doc) => handleReindex(doc.id)}
          onFolderDelete={(folder) => setDeletingFolder(folder)}
          onDocumentDelete={(doc) => setDeletingDoc(doc)}
          onDocumentMove={handleDocumentMove}
          onFolderMoved={() => undefined}
          selectedDocumentIds={selectedIds}
          allDocumentsSelected={documents.length > 0 && selectedIds.size === documents.length}
          onToggleDocument={toggleSelect}
          onToggleAllDocuments={toggleAll}
          documentCount={documents.length}
        />
      </ManagementListFrame>

      <DocumentDetailDrawer
        kbId={kbId}
        document={detailDoc}
        onClose={() => setDetailDocId(null)}
      />

      <QaPairEditor
        key={qaEditorOpen ? 'create' : editingDoc?.id ?? 'closed'}
        open={qaEditorOpen || editingDoc !== null}
        mode={editingDoc ? 'edit' : 'create'}
        initialValue={editingDoc}
        loading={documentMutations.createQa.isPending || documentMutations.updateQa.isPending}
        onSubmit={(data) => {
          if (editingDoc) {
            documentMutations.updateQa.mutate(
              { docId: editingDoc.id, data },
              {
                onSuccess: () => {
                  setEditingDoc(null);
                  toast(t('toast.updated'));
                },
                onError: () => toast(t('toast.operationFailed'), 'error'),
              },
            );
            return;
          }

          documentMutations.createQa.mutate({ ...data, folderId: currentFolderId }, {
            onSuccess: () => {
              setQaEditorOpen(false);
              toast(t('toast.created'));
            },
            onError: () => toast(t('toast.operationFailed'), 'error'),
          });
        }}
        onClose={() => {
          setQaEditorOpen(false);
          setEditingDoc(null);
        }}
      />

      <FolderCreateModal
        kbId={kbId}
        parentFolderId={currentFolderId}
        open={createFolderOpen}
        onClose={() => setCreateFolderOpen(false)}
      />

      <ConfirmDialog
        open={deletingDoc !== null}
        title="删除文档"
        description={`确定要删除「${deletingDoc?.fileName ?? 'QA 对'}」吗？`}
        confirmLabel="删除"
        loading={documentMutations.remove.isPending}
        onConfirm={() => {
          if (!deletingDoc) {
            return;
          }
          documentMutations.remove.mutate(deletingDoc.id, {
            onSuccess: () => {
              setDeletingDoc(null);
              toast(t('toast.deleted'));
            },
            onError: () => toast(t('toast.operationFailed'), 'error'),
          });
        }}
        onClose={() => setDeletingDoc(null)}
      />

      <ConfirmDialog
        open={deletingFolder !== null}
        title="删除文件夹"
        description={`确认删除「${deletingFolder?.name ?? ''}」？该文件夹下的子文件夹和文档也会被一并删除。`}
        confirmLabel="删除"
        loading={folderMutations.remove.isPending}
        onConfirm={() => {
          if (!deletingFolder) {
            return;
          }

          folderMutations.remove.mutate(deletingFolder.id, {
            onSuccess: () => {
              if (breadcrumb.some((item) => item.id === deletingFolder.id)) {
                setBreadcrumb([{ id: null, name: '全部' }]);
              }
              setDeletingFolder(null);
              toast(t('toast.deleted'));
            },
            onError: () => toast(t('toast.operationFailed'), 'error'),
          });
        }}
        onClose={() => setDeletingFolder(null)}
      />

      <ConfirmDialog
        open={batchDeleteOpen}
        title="批量删除"
        description={`确定要删除选中的 ${selectedIds.size} 个文档吗？此操作不可撤销。`}
        confirmLabel="删除"
        loading={batchActionPending === 'delete'}
        onConfirm={() => {
          void runBatchMutation(
            'delete',
            (id) => documentMutations.remove.mutateAsync(id),
            (count) => `已删除 ${count} 个文档`,
            (successCount, failedCount) => `已删除 ${successCount} 个，仍有 ${failedCount} 个删除失败`,
            (count) => `${count} 个文档删除失败`,
          ).finally(() => {
            setBatchDeleteOpen(false);
          });
        }}
        onClose={() => setBatchDeleteOpen(false)}
      />

      <QaImportDrawer
        kbId={kbId}
        folderId={currentFolderId}
        open={importQaOpen}
        onClose={() => setImportQaOpen(false)}
      />
    </>
  );
}
