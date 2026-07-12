import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus, Upload } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { RowActions } from '@/shared/ui/RowActions';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { useToast } from '@/shared/ui/Toast';
import { Pagination } from '@/shared/ui/Pagination';
import { TextField } from '@/shared/ui/FormFields';
import { ToolbarButton } from '@/shared/ui/ToolbarButton';
import { formatAdminDate } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue';
import type {
  GlossaryTermCreateRequest,
  GlossaryTermView,
} from '../../lib/contracts';
import { useGlossaryCategories } from '../../resources/category/hooks';
import { useGlossaryTerms, useGlossaryTermMutations } from '../../resources/term/hooks';
import { TermFormDrawer } from '../../resources/term/components/TermFormDrawer';
import { TermImportDrawer } from '../../resources/term/components/TermImportDrawer';

const pageSize = 10;

export function CategoryTermsTab() {
  const { t } = useTranslation(['common', 'glossary']);
  const { toast } = useToast();
  const { categoryId } = useParams<{ categoryId: string }>();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editingTerm, setEditingTerm] = useState<GlossaryTermView | null>(null);
  const [deletingTerm, setDeletingTerm] = useState<GlossaryTermView | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  const categorySelectorQuery = useGlossaryCategories({ page: 1, pageSize: 100 });
  const debouncedSearch = useDebouncedValue(search, 300);
  const termQuery = useGlossaryTerms({ categoryId, page, pageSize, search: debouncedSearch });
  const termMutations = useGlossaryTermMutations();
  const { locale } = useAdminLocale();

  const terms = termQuery.data?.items ?? [];
  const selectorCategories = useMemo(() => {
    return categorySelectorQuery.data?.items ?? [];
  }, [categorySelectorQuery.data?.items]);

  const columns: TableColumn<GlossaryTermView>[] = useMemo(() => [
      {
        key: 'term',
        header: t('glossary:termsTab.columns.term'),
        render: (row) => <span className="font-medium text-text">{row.term}</span>,
      },
      {
        key: 'synonyms',
        header: t('glossary:termsTab.columns.synonyms'),
      render: (row) =>
        row.synonyms.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {row.synonyms.map((s) => (
              <span key={s} className="rounded-full border border-border px-2 py-0.5 text-xs text-text-secondary">{s}</span>
            ))}
          </div>
        ) : (
          <span className="text-text-muted">-</span>
        ),
    },
      {
        key: 'createdAt',
        header: t('glossary:termsTab.columns.createdAt'),
        className: 'whitespace-nowrap',
        render: (row) => formatAdminDate(row.createdAtUtc, undefined, locale),
      },
      {
        key: 'actions',
        header: t('glossary:termsTab.columns.actions'),
        className: 'w-12',
        render: (row) => (
          <RowActions actions={[
            { label: t('glossary:termsTab.rowActions.edit'), onClick: () => setEditingTerm(row) },
            { label: t('glossary:termsTab.rowActions.delete'), onClick: () => setDeletingTerm(row), variant: 'danger' },
          ]} />
        ),
      },
  ], [locale, t]);

  return (
    <>
      <ManagementListFrame
        refreshing={termQuery.isFetching && !termQuery.isLoading}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <FilterToolbarActions
                onRefresh={() => termQuery.refetch()}
                refreshing={termQuery.isFetching}
                onReset={() => { setSearch(''); setPage(1); }}
              >
                <ToolbarButton variant="secondary" onClick={() => setImportOpen(true)}>
                  <Upload size={14} />
                  {t('glossary:termsTab.toolbar.import')}
                </ToolbarButton>
                <ToolbarButton variant="primary" onClick={() => setCreateOpen(true)}>
                  <Plus size={14} />
                  {t('glossary:termsTab.toolbar.create')}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
            <TextField
              label={t('glossary:termsTab.toolbar.searchLabel')}
              fieldSize="compact"
              placeholder={t('glossary:termsTab.toolbar.searchPlaceholder')}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </FilterToolbar>
        }
        error={termQuery.isError ? <InlineMessage tone="error">{getErrorMessage(termQuery.error)}</InlineMessage> : undefined}
        pagination={
          termQuery.data && termQuery.data.totalCount > 0 ? (
            <Pagination
              page={page}
              pageSize={pageSize}
              totalCount={termQuery.data.totalCount}
              onChange={setPage}
            />
          ) : undefined
        }
      >
        <DataTable
          columns={columns}
          rows={terms}
          getRowKey={(row) => row.id}
          loading={termQuery.isLoading}
          emptyState={
            <EmptyState
              title={t('glossary:termsTab.emptyTitle')}
              description={t('glossary:termsTab.emptyDescription')}
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus size={16} />
                  {t('glossary:termsTab.emptyAction')}
                </Button>
              }
            />
          }
        />
      </ManagementListFrame>

      <TermFormDrawer
        open={createOpen || editingTerm !== null}
        mode={editingTerm ? 'edit' : 'create'}
        categories={selectorCategories}
        defaultCategoryId={categoryId}
        initialValue={editingTerm}
        loading={termMutations.create.isPending || termMutations.update.isPending}
        error={termMutations.create.error ?? termMutations.update.error}
        onClose={() => {
          setCreateOpen(false);
          setEditingTerm(null);
          termMutations.create.reset();
          termMutations.update.reset();
        }}
        onSubmit={(payload) => {
          if (editingTerm) {
            termMutations.update.mutate(
              { termId: editingTerm.id, data: payload },
              { onSuccess: () => { setEditingTerm(null); toast(t('toast.updated')); } },
            );
            return;
          }

          termMutations.create.mutate(payload as GlossaryTermCreateRequest, {
            onSuccess: () => { setCreateOpen(false); toast(t('toast.created')); },
          });
        }}
      />

      <TermImportDrawer
        open={importOpen}
        categoryId={categoryId}
        onClose={() => setImportOpen(false)}
      />

      <ConfirmDialog
        open={deletingTerm !== null}
        title={t('glossary:termsTab.deleteTitle')}
        description={t('glossary:termsTab.deleteDescription', { name: deletingTerm?.term ?? '' })}
        confirmLabel={t('glossary:termsTab.confirmDelete')}
        loading={termMutations.remove.isPending}
        error={termMutations.remove.error ? getErrorMessage(termMutations.remove.error) : null}
        onClose={() => {
          setDeletingTerm(null);
          termMutations.remove.reset();
        }}
        onConfirm={() => {
          if (!deletingTerm) return;
          termMutations.remove.mutate(deletingTerm.id, {
            onSuccess: () => { setDeletingTerm(null); toast(t('toast.deleted')); },
          });
        }}
      />
    </>
  );
}
