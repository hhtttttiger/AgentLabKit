import { Handle, Position, type NodeProps, type Node, type NodeTypes } from '@xyflow/react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';
import type { SkillFlowState } from '../lib/types';

const toneMap: Record<SkillFlowState['kind'], string> = {
  start: 'border-primary/25 bg-surface',
  task: 'border-border-strong bg-surface',
  decision: 'border-warning/25 bg-surface',
  handoff: 'border-error/25 bg-surface',
  terminal: 'border-success/25 bg-surface',
};

function canReceiveConnection(kind: SkillFlowState['kind']) {
  return kind !== 'start';
}

function canEmitConnection(kind: SkillFlowState['kind']) {
  return kind !== 'terminal';
}

export function SkillFlowNodeCard({ data, selected }: NodeProps<Node<SkillFlowState>>) {
  const { t } = useTranslation('common');
  const wb = 'modules.agentManagement.skills.workbench';
  const kindLabelMap: Record<SkillFlowState['kind'], string> = {
    start: t(`${wb}.nodeLabels.start`),
    task: t(`${wb}.nodeLabels.task`),
    decision: t(`${wb}.nodeLabels.decision`),
    handoff: t(`${wb}.nodeLabels.handoff`),
    terminal: t(`${wb}.nodeLabels.terminal`),
  };
  const summary = 'question' in data ? data.question : 'goal' in data ? data.goal : null;

  return (
    <div
      className={cn(
        'min-w-[208px] max-w-[16rem] rounded-[2px] border px-4 py-3 text-left text-[12px]',
        toneMap[data.kind],
        selected && 'ring-2 ring-state-focus/35',
      )}
    >
      {canReceiveConnection(data.kind) ? <Handle type="target" position={Position.Top} className="!h-3 !w-3 !border-2 !border-surface !bg-primary" /> : null}
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">{kindLabelMap[data.kind]}</div>
        <div className="mt-1 text-[13px] font-semibold text-text">{data.title}</div>
        {summary ? <div className="mt-2 line-clamp-3 text-[12px] leading-5 text-text-secondary">{summary}</div> : null}
      </div>
      {canEmitConnection(data.kind) ? <Handle type="source" position={Position.Bottom} className="!h-3 !w-3 !border-2 !border-surface !bg-primary" /> : null}
    </div>
  );
}

export const skillFlowNodeTypes: NodeTypes = {
  start: SkillFlowNodeCard,
  task: SkillFlowNodeCard,
  decision: SkillFlowNodeCard,
  handoff: SkillFlowNodeCard,
  terminal: SkillFlowNodeCard,
};
