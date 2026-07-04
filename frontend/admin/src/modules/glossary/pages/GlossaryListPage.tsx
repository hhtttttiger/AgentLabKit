import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { PageFrame } from '@/shared/ui/PageFrame';
import { useToast } from '@/shared/ui/Toast';
import { Pagination } from '@/shared/ui/Pagination';
import { SkeletonCards } from '@/shared/ui/Skeleton';
import { TextField } from '@/shared/ui/FormFields';
import { useDebouncedValue } from '@/shared/hooks/useDebouncedValue';
import type { GlossaryCategoryCreateRequest, GlossaryCategoryView } from '../lib/contracts';
import { useGlossaryCategories, useGlossaryCategoryMutations } from '../resources/category/hooks';
import { CategoryCard } from '../resources/category/components/CategoryCard';
import { CategoryFormDrawer } from '../resources/category/components/CategoryFormDrawer';

const pageSize = 12;

export function GlossaryListPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<GlossaryCategoryView | null>(null);
  const [deletingItem, setDeletingItem] = useState<GlossaryCategoryView | null>(null);

  const debouncedSearch = useDebouncedValue(search, 300);
  const listQuery = useGlossaryCategories({ page, pageSize, search: debouncedSearch });
  const mutations = useGlossaryCategoryMutations();

  const items = listQuery.data?.items ?? [];

  return (
    <PageFrame
      title={t('modules.glossary.list.title')}
      scroll={false}
      description={t('modules.glossary.list.description')}
      actions={
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={16} />
          {t('modules.glossary.list.newCategory')}
        </Button>
      }
    >
      <ManagementListFrame
        refreshing={listQuery.isFetching}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <FilterToolbarActions
                onRefresh={() => listQuery.refetch()}
                refreshing={listQuery.isFetching}
                onReset={() => { setSearch(''); setPage(1); }}
              />
            }
          >
            <TextField
              label={t('modules.glossary.list.searchLabel')}
              fieldSize="compact"
              placeholder={t('modules.glossary.list.searchPlaceholder')}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </FilterToolbar>
        }
        pagination={
          listQuery.data && Math.ceil(listQuery.data.totalCount / pageSize) > 1 ? (
            <Pagination
              page={page}
              pageSize={pageSize}
              totalCount={listQuery.data.totalCount}
              onChange={setPage}
            />
          ) : undefined
        }
      >
        {listQuery.isLoading ? (
          <SkeletonCards />
        ) : items.length === 0 ? (
          <EmptyState
            title={t('modules.glossary.list.emptyTitle')}
            description={t('modules.glossary.list.emptyDescription')}
            action={<Button onClick={() => setCreateOpen(true)}>{t('modules.glossary.list.newCategory')}</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((category) => (
              <CategoryCard
                key={category.id}
                category={category}
                onEdit={() => setEditingItem(category)}
                onDelete={() => setDeletingItem(category)}
                onClick={() => navigate(`/glossary/${category.id}`)}
              />
            ))}
          </div>
        )}
      </ManagementListFrame>

      <CategoryFormDrawer
        open={createOpen || editingItem !== null}
        mode={editingItem ? 'edit' : 'create'}
        initialValue={editingItem}
        loading={mutations.create.isPending || mutations.update.isPending}
        error={mutations.create.error ?? mutations.update.error}
        onClose={() => {
          setCreateOpen(false);
          setEditingItem(null);
          mutations.create.reset();
          mutations.update.reset();
        }}
        onSubmit={(payload) => {
          if (editingItem) {
            mutations.update.mutate(
              { categoryId: editingItem.id, data: payload },
              { onSuccess: () => { setEditingItem(null); toast(t('toast.updated')); } },
            );
            return;
          }

          mutations.create.mutate(payload as GlossaryCategoryCreateRequest, {
            onSuccess: () => { setCreateOpen(false); toast(t('toast.created')); },
          });
        }}
      />

      <ConfirmDialog
        open={deletingItem !== null}
        title={t('modules.glossary.list.deleteTitle')}
        description={t('modules.glossary.list.deleteDescription', { name: deletingItem?.name ?? '' })}
        confirmLabel={t('modules.glossary.list.confirmDelete')}
        loading={mutations.remove.isPending}
        error={mutations.remove.error ? getErrorMessage(mutations.remove.error) : null}
        onClose={() => {
          setDeletingItem(null);
          mutations.remove.reset();
        }}
        onConfirm={() => {
          if (!deletingItem) return;
          mutations.remove.mutate(deletingItem.id, {
            onSuccess: () => { setDeletingItem(null); toast(t('toast.deleted')); },
          });
        }}
      />
    </PageFrame>
  );
}
