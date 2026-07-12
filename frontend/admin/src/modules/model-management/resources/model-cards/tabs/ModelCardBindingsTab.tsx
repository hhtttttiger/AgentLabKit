import { useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { getCapabilityLabel } from '@/shared/config/catalogOptions';
import { useModelDetail } from '../hooks';
import { useModelBindingMutations } from '../../model-bindings/hooks';
import { ModelBindingDrawer } from '../../model-bindings/ModelBindingDrawer';

export function ModelBindingsTab() {
  const { modelKey } = useParams<{ modelKey: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useTranslation(['common', 'modelManagement']);
  const detailQuery = useModelDetail(modelKey);
  const bindingMutations = useModelBindingMutations();

  const isCreating = searchParams.get('action') === 'create';

  function openCreate() {
    setSearchParams({ action: 'create' });
  }

  function closeDrawer() {
    setSearchParams({});
    bindingMutations.create.reset();
  }

  if (!modelKey) return null;

  const card = detailQuery.data;

  if (detailQuery.isError) {
    return <InlineMessage tone="error">{t('modelManagement:models.tabs.loadFailed')}</InlineMessage>;
  }

  if (!card && detailQuery.isLoading) {
    return <div className="text-sm text-text-secondary">{t('modelManagement:models.tabs.loading')}</div>;
  }

  if (!card) return null;

  const bindings = card.bindings ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">{t('modelManagement:models.tabs.bindings.description')}</p>
        <Button variant="secondary" onClick={openCreate}>{t('modelManagement:models.tabs.bindings.addButton')}</Button>
      </div>

      {bindings.length ? (
        <div className="space-y-3">
          {bindings.map((binding) => (
            <div key={binding.bindingKey} className="rounded-[2px] border border-border bg-surface/70 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-text">{binding.displayName}</div>
                  <div className="mt-1 text-xs text-text-muted">
                    {binding.bindingKey} / {getCapabilityLabel(t, binding.capability)}
                  </div>
                </div>
                <Badge tone={binding.isEnabled ? 'success' : 'warning'}>{binding.isEnabled ? t('modelManagement:models.tabs.bindings.status.enabled') : t('modelManagement:models.tabs.bindings.status.disabled')}</Badge>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title={t('modelManagement:models.tabs.bindings.empty')} />
      )}

      <ModelBindingDrawer
        open={isCreating}
        mode="create"
        initialValue={null}
        modelKeyPreset={modelKey}
        loading={bindingMutations.create.isPending}
        error={bindingMutations.create.error ? bindingMutations.getMutationMessage(bindingMutations.create.error) : null}
        onClose={closeDrawer}
        onSubmit={async (model) => {
          await bindingMutations.create.mutateAsync(model);
          closeDrawer();
        }}
      />
    </div>
  );
}
