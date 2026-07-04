import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SkillFlowOutline } from './SkillFlowOutline';
import type { SkillFlowDocument } from '../lib/types';

const document: SkillFlowDocument = {
  version: '3',
  metadata: {
    skillKey: 'branching-skill',
    displayName: '鍒嗘敮鎶€鑳?',
    description: '鍒嗘敮娴佺▼',
    version: '1.0.0',
  },
  entryStateId: 'start',
  states: {
    start: { id: 'start', kind: 'start', title: '寮€濮?' },
    safeTask: {
      id: 'safeTask',
      kind: 'task',
      title: '瀹夊叏浠诲姟',
      goal: '',
      toolPlan: [],
      inputContract: { inherited: [], required: [], optional: [] },
      outputContract: [],
      fallbackPolicy: { mode: 'stay', note: '' },
    },
    decision: {
      id: 'decision',
      kind: 'decision',
      title: '杩涘叆瀹℃壒璺緞',
      question: '璧板摢鏉¤矾寰勶紵',
    },
    joinTask: {
      id: 'joinTask',
      kind: 'task',
      title: '姹囧悎浠诲姟',
      goal: '',
      toolPlan: [],
      inputContract: { inherited: [], required: [], optional: [] },
      outputContract: [],
      fallbackPolicy: { mode: 'stay', note: '' },
    },
    end: {
      id: 'end',
      kind: 'terminal',
      title: '缁撴潫',
      outcome: 'resolved',
      resolutionNote: 'done',
    },
  },
  transitions: {
    'start-safeTask': { id: 'start-safeTask', fromStateId: 'start', toStateId: 'safeTask', label: '寮€濮?', kind: 'default', priority: 0 },
    'safeTask-end': { id: 'safeTask-end', fromStateId: 'safeTask', toStateId: 'end', label: '瀹屾垚', kind: 'default', priority: 0 },
    'start-decision': { id: 'start-decision', fromStateId: 'start', toStateId: 'decision', label: '璺敱', kind: 'default', priority: 0 },
    'decision-joinTask-a': {
      id: 'decision-joinTask-a',
      fromStateId: 'decision',
      toStateId: 'joinTask',
      label: 'A',
      kind: 'condition',
      priority: 0,
      predicate: { description: 'A', expression: { field: 'route', operator: 'eq', value: 'a' } },
    },
    'decision-joinTask-b': {
      id: 'decision-joinTask-b',
      fromStateId: 'decision',
      toStateId: 'joinTask',
      label: 'B',
      kind: 'condition',
      priority: 1,
      predicate: { description: 'B', expression: { field: 'route', operator: 'eq', value: 'b' } },
    },
    'joinTask-end': { id: 'joinTask-end', fromStateId: 'joinTask', toStateId: 'end', label: '瀹屾垚', kind: 'default', priority: 0 },
  },
};

describe('SkillFlowOutline', () => {
  it('only renders insertion affordances for graph shapes the store can safely rewrite', () => {
    render(
      <SkillFlowOutline
        document={document}
        selection={{ kind: 'state', id: 'safeTask' }}
        onSelectState={vi.fn()}
        onInsertStateBefore={vi.fn()}
        onInsertStateAfter={vi.fn()}
        onInsertDecisionAfter={vi.fn()}
      />,
    );

    const rows = screen.getAllByTestId('skill-outline-row');
    const safeRow = rows.find((row) => within(row).queryByRole('button', { name: /瀹夊叏浠诲姟/ }));
    const decisionRow = rows.find((row) => within(row).queryByRole('button', { name: /杩涘叆瀹℃壒璺緞/ }));
    const joinRow = rows.find((row) => within(row).queryByRole('button', { name: /姹囧悎浠诲姟/ }));

    expect(safeRow).toBeDefined();
    expect(within(safeRow!).getByRole('button', { name: '插入前置任务步骤' })).toBeInTheDocument();
    expect(within(safeRow!).getByRole('button', { name: '插入后置任务步骤' })).toBeInTheDocument();
    expect(within(safeRow!).getByRole('button', { name: '插入后置判断步骤' })).toBeInTheDocument();

    expect(decisionRow).toBeDefined();
    expect(within(decisionRow!).queryByRole('button', { name: '插入后置任务步骤' })).not.toBeInTheDocument();

    expect(joinRow).toBeDefined();
    expect(within(joinRow!).queryByRole('button', { name: '插入前置任务步骤' })).not.toBeInTheDocument();
  });
});
