import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { LlmModelInstanceView, LlmModelInstanceWriteModel } from '../../lib/contracts';
import { useFeatureOptions } from '../../options/hooks';
import { useModelInstanceList, useModelInstanceMutations } from './hooks';
import { defaultModelInstanceFilters, toModelInstanceQuery, type ModelInstanceFilters } from './types';

type ModelInstanceDrawerSubmitPayload = {
  modelKey: string;
  model: LlmModelInstanceWriteModel;
};

export type ModelInstancesPageState = {
  filters: ModelInstanceFilters;
  featureOptionsQuery: ReturnType<typeof useFeatureOptions>;
  listQuery: ReturnType<typeof useModelInstanceList>;
  rows: LlmModelInstanceView[];
  metrics: {
    enabledCount: number;
    healthyCount: number;
    typeCount: number;
  };
  drawer: {
    open: boolean;
    mode: 'create' | 'edit';
    initialValue: LlmModelInstanceView | null;
    loading: boolean;
    error: string | null;
    onClose: () => void;
    onSubmit: (payload: ModelInstanceDrawerSubmitPayload) => Promise<void>;
  };
  deleteDialog: {
    open: boolean;
    loading: boolean;
    description: string;
    onClose: () => void;
    onConfirm: () => Promise<void>;
  };
  patchFilters: (patch: Partial<ModelInstanceFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  openCreate: () => void;
  openEdit: (item: LlmModelInstanceView) => void;
  requestDelete: (item: LlmModelInstanceView) => void;
};

export function useModelInstancesPageState(): ModelInstancesPageState {
  const { t } = useTranslation();
  const [filters, setFilters] = useState(defaultModelInstanceFilters);
  const [editingItem, setEditingItem] = useState<LlmModelInstanceView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmModelInstanceView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const query = useMemo(() => toModelInstanceQuery(filters), [filters]);
  const featureOptionsQuery = useFeatureOptions();
  const listQuery = useModelInstanceList(query);
  const mutations = useModelInstanceMutations();
  const rows = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);

  const metrics = useMemo(
    () => ({
      enabledCount: rows.filter((item) => item.isEnabled).length,
      healthyCount: rows.filter((item) => item.isHealthy).length,
      typeCount: new Set(rows.map((item) => item.type)).size,
    }),
    [rows],
  );

  const closeDrawer = () => {
    setCreateOpen(false);
    setEditingItem(null);
    mutations.create.reset();
    mutations.update.reset();
  };

  const closeDeleteDialog = () => {
    setDeletingItem(null);
    mutations.remove.reset();
  };

  return {
    filters,
    featureOptionsQuery,
    listQuery,
    rows,
    metrics,
    drawer: {
      open: createOpen || editingItem !== null,
      mode: editingItem ? 'edit' : 'create',
      initialValue: editingItem,
      loading: mutations.create.isPending || mutations.update.isPending,
      error: mutations.create.error
        ? mutations.getMutationMessage(mutations.create.error)
        : mutations.update.error
          ? mutations.getMutationMessage(mutations.update.error)
          : null,
      onClose: closeDrawer,
      onSubmit: async ({ modelKey, model }) => {
        if (editingItem) {
          await mutations.update.mutateAsync({ instanceKey: editingItem.instanceKey, model });
          setEditingItem(null);
          return;
        }

        await mutations.create.mutateAsync({ modelKey, model });
        setCreateOpen(false);
      },
    },
    deleteDialog: {
      open: deletingItem !== null,
      loading: mutations.remove.isPending,
      description: deletingItem ? t('modules.modelManagement.modelInstances.page.deleteDescription', { name: deletingItem.instanceKey }) : '',
      onClose: closeDeleteDialog,
      onConfirm: async () => {
        if (!deletingItem) {
          return;
        }

        await mutations.remove.mutateAsync(deletingItem.instanceKey);
        setDeletingItem(null);
      },
    },
    patchFilters: (patch) => {
      setFilters((current) => ({ ...current, ...patch }));
    },
    resetFilters: () => {
      setFilters(defaultModelInstanceFilters);
    },
    setPage: (page) => {
      setFilters((current) => ({ ...current, page }));
    },
    openCreate: () => {
      setCreateOpen(true);
    },
    openEdit: (item) => {
      setEditingItem(item);
    },
    requestDelete: (item) => {
      setDeletingItem(item);
    },
  };
}
