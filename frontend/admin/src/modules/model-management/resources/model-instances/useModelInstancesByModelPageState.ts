import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { LlmModelInstanceView, LlmModelInstanceWriteModel } from '../../lib/contracts';
import { useModelList } from '../model-cards/hooks';
import { useModelInstanceMutations, useModelInstancesByModel } from './hooks';

type ModelInstanceDrawerSubmitPayload = {
  modelKey: string;
  model: LlmModelInstanceWriteModel;
};

export type ModelInstancesByModelPageState = {
  models: {
    items: { modelKey: string; displayName: string; isEnabled: boolean; instanceCount: number }[];
    isLoading: boolean;
    selectedModelKey: string | null;
    onSelect: (modelKey: string) => void;
  };
  instances: {
    items: LlmModelInstanceView[];
    isLoading: boolean;
    totalCount: number;
  };
  drawer: {
    open: boolean;
    mode: 'create' | 'edit';
    initialValue: LlmModelInstanceView | null;
    modelKeyPreset: string | null;
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
  openCreate: () => void;
  openEdit: (item: LlmModelInstanceView) => void;
  requestDelete: (item: LlmModelInstanceView) => void;
};

export function useModelInstancesByModelPageState(): ModelInstancesByModelPageState {
  const { t } = useTranslation(['common', 'modelManagement']);
  const [selectedModelKey, setSelectedModelKey] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<LlmModelInstanceView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmModelInstanceView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const modelListQuery = useModelList({ page: 1, pageSize: 100 });

  const models = useMemo(() => {
    const items = modelListQuery.data?.items ?? [];
    return items.map((m) => ({
      modelKey: m.modelKey,
      displayName: m.displayName,
      isEnabled: m.isEnabled,
      instanceCount: m.instanceCount ?? 0,
    }));
  }, [modelListQuery.data?.items]);

  useEffect(() => {
    if (models.length > 0 && !selectedModelKey) {
      setSelectedModelKey(models[0].modelKey);
    }
  }, [models, selectedModelKey]);

  const instancesQuery = useModelInstancesByModel(selectedModelKey);
  const instances = instancesQuery.data?.items ?? [];

  const mutations = useModelInstanceMutations();

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
    models: {
      items: models,
      isLoading: modelListQuery.isLoading,
      selectedModelKey,
      onSelect: setSelectedModelKey,
    },
    instances: {
      items: instances,
      isLoading: instancesQuery.isLoading,
      totalCount: instancesQuery.data?.total ?? instances.length,
    },
    drawer: {
      open: createOpen || editingItem !== null,
      mode: editingItem ? 'edit' : 'create',
      initialValue: editingItem,
      modelKeyPreset: editingItem ? null : selectedModelKey,
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
      description: deletingItem
        ? t('modelManagement:modelInstances.page.deleteDescription', { name: deletingItem.instanceKey })
        : '',
      onClose: closeDeleteDialog,
      onConfirm: async () => {
        if (!deletingItem) return;
        await mutations.remove.mutateAsync(deletingItem.instanceKey);
        setDeletingItem(null);
      },
    },
    openCreate: () => setCreateOpen(true),
    openEdit: (item) => setEditingItem(item),
    requestDelete: (item) => setDeletingItem(item),
  };
}
