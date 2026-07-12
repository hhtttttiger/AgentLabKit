/**
 * AI Chat Module - Model Selector
 * Allows users to select between Agent and ModelCard for chat
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { ModelType, ModelOption } from '../lib/contracts';

type ModelSelectorProps = {
  agentOptions: ModelOption[];
  modelOptions: ModelOption[];
  selectedModel: ModelOption | null;
  onSelect: (model: ModelOption) => void;
  variant?: 'default' | 'compact';
};

export function ModelSelector({
  agentOptions,
  modelOptions,
  selectedModel,
  onSelect,
  variant = 'default',
}: ModelSelectorProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const hasAgentOptions = agentOptions.length > 0;
  const hasCardOptions = modelOptions.length > 0;
  const [mode, setMode] = useState<ModelType>(
    selectedModel?.type || 'model'
  );

  const currentOptions = mode === 'agent' ? agentOptions : modelOptions;
  const showModeToggle = hasAgentOptions && hasCardOptions;
  const isCompact = variant === 'compact';

  useEffect(() => {
    if (selectedModel?.type && selectedModel.type !== mode) {
      setMode(selectedModel.type);
      return;
    }

    if (mode === 'agent' && !hasAgentOptions) {
      setMode('model');
      return;
    }

    if (mode === 'model' && !hasCardOptions && hasAgentOptions) {
      setMode('agent');
    }
  }, [hasAgentOptions, hasCardOptions, mode, selectedModel]);

  const handleModeChange = (newMode: ModelType) => {
    const nextOptions = newMode === 'agent' ? agentOptions : modelOptions;
    setMode(newMode);

    if (nextOptions.length > 0) {
      onSelect(nextOptions[0]);
    }
  };

  return (
    <div className={isCompact
      ? 'flex flex-wrap items-center gap-3'
      : 'flex items-center gap-3 rounded-lg border border-border bg-surface-subtle p-2'}
    >
      {showModeToggle ? (
        <div
          className={
            isCompact
              ? 'inline-flex items-center rounded-[2px] border border-[rgb(70_94_164/0.14)] bg-surface p-1 dark:border-[rgb(70_94_164/0.25)] dark:bg-surface'
              : 'flex rounded-md bg-surface p-1'
          }
        >
          <ModeButton
            active={mode === 'model'}
            onClick={() => handleModeChange('model')}
            compact={isCompact}
          >
            {t('aiChat:selector.model')}
          </ModeButton>
          <ModeButton
            active={mode === 'agent'}
            onClick={() => handleModeChange('agent')}
            compact={isCompact}
          >
            {t('aiChat:selector.agent')}
          </ModeButton>
        </div>
      ) : null}

      <div className={isCompact ? 'min-w-[200px] flex-1' : 'flex-1'}>
        <select
          value={selectedModel?.id || ''}
          onChange={(e) => {
            const option = [...agentOptions, ...modelOptions].find(
              (opt) => opt.id === e.target.value
            );
            if (option) onSelect(option);
          }}
          className={isCompact
            ? 'w-full rounded-[2px] border border-[rgb(70_94_164/0.16)] bg-white px-4 py-2.5 text-sm text-[rgb(24_33_58)] focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/15 dark:border-[rgb(70_94_164/0.25)] dark:bg-[rgb(30_41_59)] dark:text-[rgb(203_213_225)] dark:focus:border-primary/50 dark:focus:ring-primary/20'
            : 'w-full rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text focus:border-border-focus focus:outline-none focus:ring-1 focus:ring-border-focus'}
          disabled={currentOptions.length === 0}
        >
          {currentOptions.length === 0 ? (
            <option value="">
              {mode === 'agent'
                ? t('aiChat:selector.noAvailableAgent')
                : t('aiChat:selector.noAvailableModel')}
            </option>
          ) : (
            currentOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))
          )}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mode Toggle Button
// ---------------------------------------------------------------------------

type ModeButtonProps = {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  compact?: boolean;
};

function ModeButton({ active, onClick, children, compact = false }: ModeButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`${compact ? 'rounded-[2px] px-4 py-2 text-sm' : 'rounded-md px-3 py-1 text-sm'} font-medium transition-all ${
        active
          ? compact
            ? 'text-white'
            : 'bg-primary text-primary-fg'
          : compact
            ? 'text-[rgb(73_86_117)] hover:bg-white/75 hover:text-[rgb(29_41_72)] dark:text-[rgb(148_163_184)] dark:hover:bg-white/8 dark:hover:text-[rgb(226_232_240)]'
            : 'text-text-muted hover:text-text'
      }`}
      style={active && compact ? {
        background: 'rgb(var(--color-primary))',
      } : undefined}
      type="button"
    >
      {children}
    </button>
  );
}
