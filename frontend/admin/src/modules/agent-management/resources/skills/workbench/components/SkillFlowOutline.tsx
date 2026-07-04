import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GitBranch, Plus } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import type { SkillFlowDocument } from '../lib/types';
import { canInsertTaskStateAfter, canInsertTaskStateBefore } from '../state/useSkillFlowBuilderStore';

function SkillFlowOutlineRow({
  id,
  kind,
  title,
  canInsertBefore,
  canInsertAfter,
  active,
  shouldReceiveFocus,
  onFocused,
  onSelect,
  onInsertBefore,
  onInsertAfter,
  onInsertDecisionAfter,
}: {
  id: string;
  kind: string;
  title: string;
  canInsertBefore: boolean;
  canInsertAfter: boolean;
  active: boolean;
  shouldReceiveFocus: boolean;
  onFocused: () => void;
  onSelect: (id: string) => void;
  onInsertBefore: (id: string) => void;
  onInsertAfter: (id: string) => void;
  onInsertDecisionAfter: (id: string) => void;
}) {
  const { t } = useTranslation('common');
  const wb = 'modules.agentManagement.skills.workbench';
  const kindLabelMap: Record<string, string> = {
    task: t(`${wb}.nodeLabels.task`),
    decision: t(`${wb}.nodeLabels.decision`),
    handoff: t(`${wb}.nodeLabels.handoff`),
    terminal: t(`${wb}.nodeLabels.terminal`),
  };
  const itemRef = useRef<HTMLButtonElement | null>(null);
  const [hovered, setHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);

  useEffect(() => {
    if (!shouldReceiveFocus) {
      return;
    }

    itemRef.current?.focus();
    onFocused();
  }, [onFocused, shouldReceiveFocus]);

  const isExpanded = hovered || focusWithin;

  return (
    <div
      data-testid="skill-outline-row"
      data-outline-active={isExpanded ? 'true' : 'false'}
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocusWithin(true)}
      onBlur={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
          return;
        }
        setFocusWithin(false);
      }}
    >
      {canInsertBefore ? (
        <button
          type="button"
          aria-label={t(`${wb}.outline.insertBefore`)}
          className="absolute -top-2 left-1/2 z-10 hidden -translate-x-1/2 rounded-full border border-border bg-surface p-1 text-text-secondary hover:bg-background-subtle data-[visible=true]:inline-flex"
          data-visible={isExpanded ? 'true' : 'false'}
          onClick={() => onInsertBefore(id)}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      ) : null}
      <button
        ref={itemRef}
        type="button"
        onClick={() => onSelect(id)}
        className={cn(
          'w-full rounded-[2px] border border-border bg-surface px-3 py-3 text-left transition hover:bg-background-subtle',
          active && 'border-primary/25 bg-primary/5',
        )}
      >
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">{kindLabelMap[kind] ?? kind}</div>
        <div className="mt-1 text-[13px] font-semibold text-text">{title}</div>
      </button>
      {canInsertAfter ? (
        <div
          className="absolute -bottom-3 left-1/2 z-10 hidden -translate-x-1/2 items-center gap-1 data-[visible=true]:inline-flex"
          data-visible={isExpanded ? 'true' : 'false'}
        >
          <button
            type="button"
            aria-label={t(`${wb}.outline.insertAfter`)}
            className="inline-flex rounded-full border border-border bg-surface p-1 text-text-secondary hover:bg-background-subtle"
            onClick={() => onInsertAfter(id)}
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            aria-label={t(`${wb}.outline.insertDecisionAfter`)}
            className="inline-flex rounded-full border border-border bg-surface p-1 text-text-secondary hover:bg-background-subtle"
            onClick={() => onInsertDecisionAfter(id)}
          >
            <GitBranch className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function SkillFlowOutline(props: {
  document: SkillFlowDocument;
  selection: { kind: 'state' | 'transition'; id: string } | null;
  onSelectState: (id: string) => void;
  onInsertStateBefore: (id: string) => void;
  onInsertStateAfter: (id: string) => void;
  onInsertDecisionAfter: (id: string) => void;
}) {
  const authorableStates = Object.values(props.document.states).filter(
    (state) => state.kind !== 'start',
  );
  const [shouldFocusSelection, setShouldFocusSelection] = useState(false);

  return (
    <div className="min-h-0 space-y-3 overflow-auto">
      {authorableStates.map((state) => (
        <SkillFlowOutlineRow
          key={state.id}
          id={state.id}
          kind={state.kind}
          title={state.title}
          canInsertBefore={canInsertTaskStateBefore(props.document, state.id)}
          canInsertAfter={canInsertTaskStateAfter(props.document, state.id)}
          active={props.selection?.kind === 'state' && props.selection.id === state.id}
          shouldReceiveFocus={shouldFocusSelection && props.selection?.kind === 'state' && props.selection.id === state.id}
          onFocused={() => setShouldFocusSelection(false)}
          onSelect={props.onSelectState}
          onInsertBefore={(id) => {
            setShouldFocusSelection(true);
            props.onInsertStateBefore(id);
          }}
          onInsertAfter={(id) => {
            setShouldFocusSelection(true);
            props.onInsertStateAfter(id);
          }}
          onInsertDecisionAfter={(id) => {
            setShouldFocusSelection(true);
            props.onInsertDecisionAfter(id);
          }}
        />
      ))}
    </div>
  );
}
