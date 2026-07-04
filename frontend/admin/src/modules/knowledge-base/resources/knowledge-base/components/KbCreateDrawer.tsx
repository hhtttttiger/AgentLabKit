import { useEffect, useState } from 'react';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { NumberField, SelectField, TextAreaField, TextField, ToggleField } from '@/shared/ui/FormFields';
import type { KbView } from '../../../lib/contracts';
import {
  createDefaultKbSettings,
  parseKbSettingsJson,
  serializeKbSettings,
  type KbSettingsFormState,
} from '../settings';

// Azure provider 与 Azure Chunk Push 已下线，新增/编辑固定使用 local 提供方。
const LOCAL_ONLY_SETTINGS = { provider: 'local' as const, recallSources: [] };

export function KbCreateDrawer({
  open,
  mode,
  initialValue,
  loading,
  onSubmit,
  onClose,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  initialValue: KbView | null;
  loading: boolean;
  onSubmit: (data: { name: string; description?: string; settingsJson?: string }) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(initialValue?.name ?? '');
  const [description, setDescription] = useState(initialValue?.description ?? '');
  const [settings, setSettings] = useState<KbSettingsFormState>(() => ({
    ...parseKbSettingsJson(initialValue?.settingsJson),
    ...LOCAL_ONLY_SETTINGS,
  }));

  useEffect(() => {
    if (!open) {
      return;
    }

    setName(initialValue?.name ?? '');
    setDescription(initialValue?.description ?? '');
    setSettings({ ...parseKbSettingsJson(initialValue?.settingsJson), ...LOCAL_ONLY_SETTINGS });
  }, [initialValue, open]);

  const handleClose = () => {
    setName('');
    setDescription('');
    setSettings(createDefaultKbSettings());
    onClose();
  };

  const updateLocal = <T extends keyof KbSettingsFormState['local']>(
    key: T,
    value: KbSettingsFormState['local'][T],
  ) => {
    setSettings((current) => ({
      ...current,
      local: {
        ...current.local,
        [key]: value,
      },
    }));
  };

  const saveDisabled = loading || !name.trim();

  const handleSubmit = () => {
    if (saveDisabled) return;
    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      settingsJson: serializeKbSettings(settings),
    });
  };

  return (
    <FormModal
      open={open}
      title={mode === 'create' ? '创建知识库' : '编辑知识库'}
      onClose={handleClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={saveDisabled}>
            {loading ? '处理中...' : mode === 'create' ? '创建' : '保存'}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        <TextField
          label="名称"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="输入知识库名称"
        />
        <TextAreaField
          label="描述"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="输入知识库描述（可选）"
        />
        <div className="rounded-[2px] border border-border bg-surface/70 p-4">
          <div className="mb-4 text-sm font-medium text-text">RAG 配置</div>
          <div className="space-y-4">
            <SelectField
              label="Provider"
              disabled={mode === 'edit'}
              hint={mode === 'edit' ? '创建后不可修改，避免索引损坏。' : undefined}
              value={settings.provider}
              onChange={() => setSettings((current) => ({ ...current, ...LOCAL_ONLY_SETTINGS }))}
            >
              <option value="local">Local</option>
            </SelectField>

            <div className="grid gap-4 md:grid-cols-2">
              <NumberField
                label="Chunk 长度"
                min={1}
                value={String(settings.local.maxLength)}
                onChange={(e) => updateLocal('maxLength', Number(e.target.value || 0))}
              />
              <NumberField
                label="Chunk 重叠"
                min={0}
                value={String(settings.local.overlap)}
                onChange={(e) => updateLocal('overlap', Number(e.target.value || 0))}
              />
            </div>
            <TextField
              label="Splitter"
              value={settings.local.splitter}
              onChange={(e) => updateLocal('splitter', e.target.value)}
            />
            <div className="grid gap-3 md:grid-cols-2">
              <ToggleField
                label="Embedding 索引"
                hint="保留向量召回。"
                checked={settings.local.indexes.includes('embedding')}
                onChange={(checked) =>
                  updateLocal(
                    'indexes',
                    checked
                      ? Array.from(new Set([...settings.local.indexes, 'embedding']))
                      : settings.local.indexes.filter((item) => item !== 'embedding'),
                  )
                }
              />
              <ToggleField
                label="Full Text 索引"
                hint="保留词法召回。"
                checked={settings.local.indexes.includes('full_text')}
                onChange={(checked) =>
                  updateLocal(
                    'indexes',
                    checked
                      ? Array.from(new Set([...settings.local.indexes, 'full_text']))
                      : settings.local.indexes.filter((item) => item !== 'full_text'),
                  )
                }
              />
            </div>
          </div>
        </div>
      </div>
    </FormModal>
  );
}
