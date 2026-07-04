import { useState } from 'react';
import { FileText, Folder, HelpCircle } from 'lucide-react';
import { RowActions } from '@/shared/ui/RowActions';
import { FolderMoveModal } from '../../../resources/folder/components/FolderMoveModal';
import { ProcessingStatusBadge } from '../../../resources/document/components/ProcessingStatusBadge';
import type { KbDocumentView, KbFolderView } from '../../../lib/contracts';

export type UnifiedListItem =
  | { type: 'folder'; data: KbFolderView }
  | { type: 'document'; data: KbDocumentView };

type Props = {
  kbId: string;
  items: UnifiedListItem[];
  onFolderClick: (folder: KbFolderView) => void;
  onDocumentClick: (doc: KbDocumentView) => void;
  onDocumentEdit?: (doc: KbDocumentView) => void;
  onDocumentReindex?: (doc: KbDocumentView) => void;
  onFolderDelete: (folder: KbFolderView) => void;
  onDocumentDelete: (doc: KbDocumentView) => void;
  onDocumentMove: (docId: string, targetFolderId: string | null) => Promise<void>;
  onFolderMoved: () => void;
  selectedDocumentIds?: Set<string>;
  allDocumentsSelected?: boolean;
  onToggleDocument?: (docId: string) => void;
  onToggleAllDocuments?: () => void;
  documentCount?: number;
};

export function KbUnifiedList({
  kbId,
  items,
  onFolderClick,
  onDocumentClick,
  onDocumentEdit,
  onDocumentReindex,
  onFolderDelete,
  onDocumentDelete,
  onDocumentMove,
  onFolderMoved,
  selectedDocumentIds,
  allDocumentsSelected,
  onToggleDocument,
  onToggleAllDocuments,
  documentCount = 0,
}: Props) {
  const [movingDocId, setMovingDocId] = useState<string | null>(null);
  const [movingFolderId, setMovingFolderId] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className="rounded-[2px] border border-dashed border-border bg-background-subtle px-6 py-16 text-center text-sm text-text-secondary">
        当前目录为空
      </div>
    );
  }

  return (
    <>
      <div className="overflow-hidden rounded-[2px] border border-border bg-surface">
        {documentCount > 0 && onToggleAllDocuments ? (
          <div className="flex items-center gap-3 border-b border-border bg-background-subtle px-4 py-2.5 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={!!allDocumentsSelected}
              onChange={onToggleAllDocuments}
              className="accent-primary"
            />
            <span>全选当前目录文档</span>
          </div>
        ) : null}
        {items.map((item, index) => {
          const rowClassName = `group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-state-hover ${
            index < items.length - 1 ? 'border-b border-border' : ''
          }`;

          if (item.type === 'folder') {
            const folder = item.data;
            return (
              <div key={`folder-${folder.id}`} className={rowClassName}>
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                  onClick={() => onFolderClick(folder)}
                >
                  <Folder size={16} className="shrink-0 text-text-secondary" />
                  <span className="truncate text-sm font-medium text-text">{folder.name}</span>
                </button>
                <span className="text-xs text-text-muted">文件夹</span>
                <RowActions actions={[
                  { label: '移动', onClick: () => setMovingFolderId(folder.id) },
                  { label: '删除', onClick: () => onFolderDelete(folder), variant: 'danger' },
                ]} />
              </div>
            );
          }

          const doc = item.data;
          const title = doc.fileName ?? doc.qaQuestion ?? '—';
          return (
            <div key={`doc-${doc.id}`} className={rowClassName}>
              {onToggleDocument ? (
                <input
                  type="checkbox"
                  checked={selectedDocumentIds?.has(doc.id) ?? false}
                  onChange={() => onToggleDocument(doc.id)}
                  className="shrink-0 accent-primary"
                />
              ) : null}
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-3 text-left"
                onClick={() => onDocumentClick(doc)}
              >
                {doc.sourceType === 'QaPair' ? (
                  <HelpCircle size={16} className="shrink-0 text-text-secondary" />
                ) : (
                  <FileText size={16} className="shrink-0 text-text-secondary" />
                )}
                <span className="truncate text-sm text-text">{title}</span>
              </button>
              <ProcessingStatusBadge status={doc.ingestStatus} />
              <RowActions actions={[
                ...(doc.sourceType === 'QaPair' && onDocumentEdit
                  ? [{ label: '编辑', onClick: () => onDocumentEdit(doc) }]
                  : []),
                ...(onDocumentReindex ? [{ label: '重新索引', onClick: () => onDocumentReindex(doc) }] : []),
                { label: '移动', onClick: () => setMovingDocId(doc.id) },
                { label: '删除', onClick: () => onDocumentDelete(doc), variant: 'danger' },
              ]} />
            </div>
          );
        })}
      </div>

      {movingDocId ? (
        <FolderMoveModal
          kbId={kbId}
          itemId={movingDocId}
          itemType="document"
          open={!!movingDocId}
          onClose={() => setMovingDocId(null)}
          onMoveDocument={async (targetFolderId) => {
            await onDocumentMove(movingDocId, targetFolderId);
            setMovingDocId(null);
          }}
        />
      ) : null}

      {movingFolderId ? (
        <FolderMoveModal
          kbId={kbId}
          itemId={movingFolderId}
          itemType="folder"
          excludeFolderId={movingFolderId}
          open={!!movingFolderId}
          onClose={() => {
            setMovingFolderId(null);
            onFolderMoved();
          }}
        />
      ) : null}
    </>
  );
}
