import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PageFrame } from '@/shared/ui/PageFrame';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { TextField, SelectField } from '@/shared/ui/FormFields';
import { useKbList, useKbMutations } from '../resources/knowledge-base/hooks';
import { defaultKbListFilters } from '../resources/knowledge-base/types';
import type { KbListFilters } from '../resources/knowledge-base/types';
import type { KbView } from '../lib/contracts';
import { KbCardView } from '../resources/knowledge-base/components/KbCardView';
import { KbCreateDrawer } from '../resources/knowledge-base/components/KbCreateDrawer';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { Pagination } from '@/shared/ui/Pagination';
import { SkeletonCards } from '@/shared/ui/Skeleton';

export function KnowledgeBaseListPage() {
  const { t } = useTranslation('common');
  const navigate = useNavigate();
  const [filters, setFilters] = useState<KbListFilters>(defaultKbListFilters);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<KbView | null>(null);
  const [deletingItem, setDeletingItem] = useState<KbView | null>(null);

  const listQuery = useKbList(filters);
  const mutations = useKbMutations({
    onCreated: (id) => navigate(`/knowledge-base/${id}`),
  });

  const items = listQuery.data?.items ?? [];

  return (
    <PageFrame
      title={t('modules.knowledgeBase.list.title')}
      scroll={false}
      description={t('modules.knowledgeBase.list.description')}
      actions={
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={16} />
          {t('modules.knowledgeBase.list.create')}
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
                onReset={() => setFilters(defaultKbListFilters)}
              />
            }
          >
            <TextField
              label={t('modules.knowledgeBase.list.searchLabel')}
              fieldSize="compact"
              placeholder={t('modules.knowledgeBase.list.searchPlaceholder')}
              value={filters.keyword}
              onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value, page: 1 }))}
            />
            <SelectField
              label={t('modules.knowledgeBase.list.statusLabel')}
              fieldSize="compact"
              value={filters.status}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value as KbListFilters['status'], page: 1 }))}
            >
              <option value="all">{t('modules.knowledgeBase.list.statuses.all')}</option>
              <option value="Active">{t('modules.knowledgeBase.list.statuses.active')}</option>
              <option value="Processing">{t('modules.knowledgeBase.list.statuses.processing')}</option>
              <option value="Disabled">{t('modules.knowledgeBase.list.statuses.disabled')}</option>
            </SelectField>
          </FilterToolbar>
        }
        pagination={
          listQuery.data && Math.ceil(listQuery.data.totalCount / filters.pageSize) > 1 ? (
            <Pagination
              page={filters.page}
              pageSize={filters.pageSize}
              totalCount={listQuery.data.totalCount}
              onChange={(p) => setFilters((f) => ({ ...f, page: p }))}
            />
          ) : undefined
        }
      >
        {/* Card Grid */}
        {listQuery.isLoading ? (
          <SkeletonCards />
        ) : items.length === 0 ? (
          <EmptyState
            title={t('modules.knowledgeBase.list.emptyTitle')}
            description={t('modules.knowledgeBase.list.emptyDescription')}
            action={<Button onClick={() => setCreateOpen(true)}>{t('modules.knowledgeBase.list.create')}</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((kb) => (
              <KbCardView
                key={kb.id}
                kb={kb}
                onEdit={() => setEditingItem(kb)}
                onDelete={() => setDeletingItem(kb)}
                onClick={() => navigate(`/knowledge-base/${kb.id}`)}
              />
            ))}
          </div>
        )}
      </ManagementListFrame>

      {/* Create/Edit Drawer */}
      <KbCreateDrawer
        open={createOpen || editingItem !== null}
        mode={editingItem ? 'edit' : 'create'}
        initialValue={editingItem}
        loading={mutations.create.isPending || mutations.update.isPending}
        onSubmit={(data) => {
          if (editingItem) {
            mutations.update.mutate(
              { kbId: editingItem.id, data },
              { onSuccess: () => setEditingItem(null) },
            );
          } else {
            mutations.create.mutate(data, {
              onSuccess: () => setCreateOpen(false),
            });
          }
        }}
        onClose={() => {
          setCreateOpen(false);
          setEditingItem(null);
        }}
      />

      {/* Delete Confirm */}
      <ConfirmDialog
        open={deletingItem !== null}
        title={t('modules.knowledgeBase.list.deleteTitle')}
        description={t('modules.knowledgeBase.list.deleteDescription', { name: deletingItem?.name ?? '' })}
        confirmLabel={t('actions.delete')}
        loading={mutations.remove.isPending}
        onConfirm={() => {
          if (deletingItem) {
            mutations.remove.mutate(deletingItem.id, {
              onSuccess: () => setDeletingItem(null),
            });
          }
        }}
        onClose={() => setDeletingItem(null)}
      />
    </PageFrame>
  );
}
