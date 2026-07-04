import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useToast } from '@/shared/ui/Toast';
import type { LlmModelView, LlmModelWriteModel } from '../../lib/contracts';
import { useFeatureOptions } from '../../options/hooks';
import { useModelList, useModelMutations } from './hooks';
import { defaultModelFilters, toModelQuery, type ModelFilters } from './types';

export type ModelsPageState = {
  filters: ModelFilters;
  featureOptionsQuery: ReturnType<typeof useFeatureOptions>;
  listQuery: ReturnType<typeof useModelList>;
  rows: LlmModelView[];
  metrics: {
    enabledCount: number;
    withInstances: number;
    withBindings: number;
  };
  drawer: {
    open: boolean;
    mode: 'create' | 'edit';
    initialValue: LlmModelView | null;
    loading: boolean;
    error: string | null;
    onClose: () => void;
    onSubmit: (model: LlmModelWriteModel, options: { navigateToDetail?: boolean }) => Promise<void>;
  };
  deleteDialog: {
    open: boolean;
    loading: boolean;
    description: string;
    onClose: () => void;
    onConfirm: () => Promise<void>;
  };
  testDialog: {
    open: boolean;
    model: LlmModelView | null;
    onClose: () => void;
  };
  embeddingTestDialog: {
    open: boolean;
    model: LlmModelView | null;
    onClose: () => void;
  };
  patchFilters: (patch: Partial<ModelFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  openCreate: () => void;
  openEdit: (item: LlmModelView) => void;
  requestDelete: (item: LlmModelView) => void;
  openTest: (item: LlmModelView) => void;
  openEmbeddingTest: (item: LlmModelView) => void;
};

export function useModelsPageState(): ModelsPageState {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { toast } = useToast();
  const [filters, setFilters] = useState(defaultModelFilters);
  const [editingItem, setEditingItem] = useState<LlmModelView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmModelView | null>(null);
  const [testingItem, setTestingItem] = useState<LlmModelView | null>(null);
  const [embeddingTestingItem, setEmbeddingTestingItem] = useState<LlmModelView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [navigateToDetailAfterCreate, setNavigateToDetailAfterCreate] = useState(false);

  const query = useMemo(() => toModelQuery(filters), [filters]);
  const featureOptionsQuery = useFeatureOptions();
  const listQuery = useModelList(query);
  const mutations = useModelMutations({
    onCreated: (modelKey) => {
      if (navigateToDetailAfterCreate) {
        navigate(`/model-management/models/${modelKey}`);
      }
    },
  });
  const rows = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);

  const metrics = useMemo(
    () => ({
      enabledCount: rows.filter((item) => item.isEnabled).length,
      withInstances: rows.filter((item) => (item.instances ?? []).length > 0).length,
      withBindings: rows.filter((item) => (item.bindings ?? []).length > 0).length,
    }),
    [rows],
  );

  const closeDrawer = useCallback(() => {
    setCreateOpen(false);
    setEditingItem(null);
    setNavigateToDetailAfterCreate(false);
    mutations.create.reset();
    mutations.update.reset();
  }, [mutations.create, mutations.update]);

  const closeDeleteDialog = useCallback(() => {
    setDeletingItem(null);
    mutations.remove.reset();
  }, [mutations.remove]);

  const patchFilters = useCallback((patch: Partial<ModelFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(defaultModelFilters);
  }, []);

  const setPage = useCallback((page: number) => {
    setFilters((current) => ({ ...current, page }));
  }, []);

  const openCreate = useCallback(() => {
    setCreateOpen(true);
  }, []);

  const openEdit = useCallback((item: LlmModelView) => {
    setEditingItem(item);
  }, []);

  const requestDelete = useCallback((item: LlmModelView) => {
    setDeletingItem(item);
  }, []);

  const openTest = useCallback((item: LlmModelView) => {
    setTestingItem(item);
  }, []);

  const openEmbeddingTest = useCallback((item: LlmModelView) => {
    setEmbeddingTestingItem(item);
  }, []);

  const drawer = useMemo(
    () => ({
      open: createOpen || editingItem !== null,
      mode: (editingItem ? 'edit' : 'create') as 'create' | 'edit',
      initialValue: editingItem,
      loading: mutations.create.isPending || mutations.update.isPending,
      error: mutations.create.error
        ? mutations.getMutationMessage(mutations.create.error)
        : mutations.update.error
          ? mutations.getMutationMessage(mutations.update.error)
          : null,
      onClose: closeDrawer,
      onSubmit: async (model: LlmModelWriteModel, options: { navigateToDetail?: boolean }) => {
        if (editingItem) {
          await mutations.update.mutateAsync({ modelKey: editingItem.modelKey, model });
          setEditingItem(null);
          toast(t('toast.updated'));
          return;
        }

        setNavigateToDetailAfterCreate(options.navigateToDetail ?? false);
        await mutations.create.mutateAsync(model);
        setCreateOpen(false);
        toast(t('toast.created'));
      },
    }),
    [createOpen, editingItem, mutations.create, mutations.update, closeDrawer, toast, t],
  );

  const deleteDialog = useMemo(
    () => ({
      open: deletingItem !== null,
      loading: mutations.remove.isPending,
      description: deletingItem
        ? t('modules.modelManagement.models.deleteDialog.description', { name: deletingItem.displayName })
        : '',
      onClose: closeDeleteDialog,
      onConfirm: async () => {
        if (!deletingItem) {
          return;
        }

        await mutations.remove.mutateAsync(deletingItem.modelKey);
        setDeletingItem(null);
        toast(t('toast.deleted'));
      },
    }),
    [deletingItem, mutations.remove, closeDeleteDialog, toast, t],
  );

  const testDialog = useMemo(
    () => ({
      open: testingItem !== null,
      model: testingItem,
      onClose: () => setTestingItem(null),
    }),
    [testingItem],
  );

  const embeddingTestDialog = useMemo(
    () => ({
      open: embeddingTestingItem !== null,
      model: embeddingTestingItem,
      onClose: () => setEmbeddingTestingItem(null),
    }),
    [embeddingTestingItem],
  );

  return useMemo(
    () => ({
      filters,
      featureOptionsQuery,
      listQuery,
      rows,
      metrics,
      drawer,
      deleteDialog,
      testDialog,
      embeddingTestDialog,
      patchFilters,
      resetFilters,
      setPage,
      openCreate,
      openEdit,
      requestDelete,
      openTest,
      openEmbeddingTest,
    }),
    [
      filters, featureOptionsQuery, listQuery, rows, metrics,
      drawer, deleteDialog, testDialog, embeddingTestDialog,
      patchFilters, resetFilters, setPage,
      openCreate, openEdit, requestDelete, openTest, openEmbeddingTest,
    ],
  );
}
