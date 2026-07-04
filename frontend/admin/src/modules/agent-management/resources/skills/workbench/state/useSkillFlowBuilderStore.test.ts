import { act } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import {
  canInsertTaskStateAfter,
  canInsertTaskStateBefore,
  createSkillFlowBuilderStore,
  type AddDecisionLabels,
  type AddTaskBranchLabels,
} from './useSkillFlowBuilderStore';
import type { SkillFlowDocument } from '../lib/types';

const stubDecisionLabels: AddDecisionLabels = {
  decisionTitle: 'Decision',
  decisionQuestion: 'Choose a branch',
  enterLabel: 'Enter decision',
  continueLabel: 'Continue',
  continueDescription: 'Continue when conditions are met',
  handoffBranchLabel: 'Hand off',
  handoffTitle: 'Handoff',
  handoffSummary: 'Hand off to agent.',
};

const stubFallbackNote = 'Route to fallback on failure.';

const stubTaskBranchLabelsFallbackHandoff: AddTaskBranchLabels = {
  transitionLabel: 'Fallback handoff',
  fallbackNote: stubFallbackNote,
  handoffTitle: 'Handoff',
  handoffSummary: 'Hand off to agent.',
  terminalTitle: 'Done',
  terminalNote: 'Flow complete.',
};

const stubTaskBranchLabelsError: AddTaskBranchLabels = {
  transitionLabel: 'Error end',
  fallbackNote: stubFallbackNote,
  handoffTitle: 'Handoff',
  handoffSummary: 'Hand off to agent.',
  terminalTitle: 'Done',
  terminalNote: 'Flow complete.',
};

const document: SkillFlowDocument = {
  version: '3',
  metadata: {
    skillKey: 'refund-orchestration',
    displayName: '退款编排',
    description: '退款路由流程',
    version: '1.0.0',
  },
  entryStateId: 'start',
  states: {
    start: { id: 'start', kind: 'start', title: '开始' },
    intake: {
      id: 'intake',
      kind: 'task',
      title: '收集上下文',
      goal: '收集退款上下文',
      toolPlan: [],
      inputContract: { inherited: [], required: [], optional: [] },
      outputContract: [],
      fallbackPolicy: { mode: 'stay', note: '继续追问缺失信息' },
    },
    resolved: { id: 'resolved', kind: 'terminal', title: '已解决', outcome: 'resolved', resolutionNote: 'done' },
  },
  transitions: {
    'start-intake': { id: 'start-intake', fromStateId: 'start', toStateId: 'intake', label: '开始', kind: 'default', priority: 0 },
    'intake-resolved': { id: 'intake-resolved', fromStateId: 'intake', toStateId: 'resolved', label: '完成', kind: 'default', priority: 0 },
  },
};

const branchingDocument: SkillFlowDocument = {
  version: '3',
  metadata: {
    skillKey: 'branching-skill',
    displayName: '分支技能',
    description: '分支流程',
    version: '1.0.0',
  },
  entryStateId: 'start',
  states: {
    start: { id: 'start', kind: 'start', title: '开始' },
    decision: {
      id: 'decision',
      kind: 'decision',
      title: '判断',
      question: '走哪条路径？',
    },
    joinTask: {
      id: 'joinTask',
      kind: 'task',
      title: '汇合任务',
      goal: '',
      toolPlan: [],
      inputContract: { inherited: [], required: [], optional: [] },
      outputContract: [],
      fallbackPolicy: { mode: 'stay', note: '' },
    },
    end: {
      id: 'end',
      kind: 'terminal',
      title: '结束',
      outcome: 'resolved',
      resolutionNote: 'done',
    },
  },
  transitions: {
    'start-decision': { id: 'start-decision', fromStateId: 'start', toStateId: 'decision', label: '路由', kind: 'default', priority: 0 },
    'decision-joinTask-a': {
      id: 'decision-joinTask-a',
      fromStateId: 'decision',
      toStateId: 'joinTask',
      label: '路径 A',
      kind: 'condition',
      priority: 0,
      predicate: { description: 'A', expression: { field: 'route', operator: 'eq', value: 'a' } },
    },
    'decision-joinTask-b': {
      id: 'decision-joinTask-b',
      fromStateId: 'decision',
      toStateId: 'joinTask',
      label: '路径 B',
      kind: 'condition',
      priority: 1,
      predicate: { description: 'B', expression: { field: 'route', operator: 'eq', value: 'b' } },
    },
    'joinTask-end': { id: 'joinTask-end', fromStateId: 'joinTask', toStateId: 'end', label: '完成', kind: 'default', priority: 0 },
  },
};

function createLoadedStore(source: SkillFlowDocument = document) {
  const store = createSkillFlowBuilderStore();

  act(() => {
    store.getState().load(source);
  });

  return store;
}

describe('createSkillFlowBuilderStore', () => {
  test('only allows insertion around states with a single default edge on the rewritten side', () => {
    expect(canInsertTaskStateBefore(document, 'intake')).toBe(true);
    expect(canInsertTaskStateAfter(document, 'intake')).toBe(true);
    expect(canInsertTaskStateAfter(branchingDocument, 'decision')).toBe(false);
    expect(canInsertTaskStateBefore(branchingDocument, 'joinTask')).toBe(false);
  });

  test('load hydrates document, compiled graph state, and selects the first editable step', () => {
    const store = createLoadedStore();
    const state = store.getState();

    expect(state.document?.entryStateId).toBe('start');
    expect(state.compiled?.validation.errors).toEqual([]);
    expect(state.nodes).toHaveLength(3);
    expect(state.edges).toHaveLength(2);
    expect(state.selection).toEqual({ kind: 'state', id: 'intake' });
  });

  test('onNodesChange updates positions and keeps compiled flow available', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().onNodesChange([
        { id: 'intake', type: 'position', position: { x: 480, y: 240 }, dragging: false },
      ]);
    });

    const state = store.getState();
    const intakeNode = state.nodes.find((node) => node.id === 'intake');

    expect(intakeNode?.position).toEqual({ x: 480, y: 240 });
    expect(state.compiled?.entryStateId).toBe('start');
    expect(state.dirty).toBe(true);
  });

  test('onEdgesChange rebuilds the document and surfaces validation errors', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().onEdgesChange([
        { id: 'intake-resolved', type: 'remove' },
      ]);
    });

    const state = store.getState();

    expect(state.document?.transitions['intake-resolved']).toBeUndefined();
    expect(state.compiled?.validation.errors).toContain('任务节点 "intake" 必须保留 1 条默认流转。');
  });

  test('addDecisionAfterState rewires the original default path through the new decision', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addDecisionAfterState('intake', stubDecisionLabels);
    });

    const state = store.getState();
    const decisionState = Object.values(state.document?.states ?? {}).find(
      (node) => node.kind === 'decision',
    );

    expect(decisionState).toBeDefined();
    expect(state.document?.transitions['intake-resolved']?.toStateId).toBe(decisionState?.id);

    const bridgedTransition = Object.values(state.document?.transitions ?? {}).find(
      (transition) => transition.fromStateId === decisionState?.id && transition.toStateId === 'resolved',
    );
    expect(bridgedTransition).toBeDefined();
    expect(state.selection).toEqual({ kind: 'state', id: decisionState?.id });
  });

  test('addTaskStateAfterState inserts a task between the selected state and its default successor', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addTaskStateAfterState('intake', 'New step');
    });

    const state = store.getState();
    const insertedState = Object.values(state.document?.states ?? {}).find(
      (node) => node.kind === 'task' && node.id !== 'intake',
    );

    expect(insertedState).toBeDefined();
    expect(state.document?.transitions['intake-resolved']?.toStateId).toBe(insertedState?.id);

    const bridgedTransition = Object.values(state.document?.transitions ?? {}).find(
      (transition) => transition.fromStateId === insertedState?.id && transition.toStateId === 'resolved',
    );
    expect(bridgedTransition).toBeDefined();
    expect(Object.keys(state.document?.states ?? {})).toEqual(['start', 'intake', insertedState?.id ?? '', 'resolved']);
    expect(state.selection).toEqual({ kind: 'state', id: insertedState?.id });
  });

  test('addTaskStateBeforeState inserts a task between the upstream default path and the selected state', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addTaskStateBeforeState('intake', 'New step');
    });

    const state = store.getState();
    const insertedState = Object.values(state.document?.states ?? {}).find(
      (node) => node.kind === 'task' && node.id !== 'intake',
    );

    expect(insertedState).toBeDefined();
    expect(state.document?.transitions['start-intake']?.toStateId).toBe(insertedState?.id);

    const bridgedTransition = Object.values(state.document?.transitions ?? {}).find(
      (transition) => transition.fromStateId === insertedState?.id && transition.toStateId === 'intake',
    );
    expect(bridgedTransition).toBeDefined();
    expect(Object.keys(state.document?.states ?? {})).toEqual(['start', insertedState?.id ?? '', 'intake', 'resolved']);
    expect(state.selection).toEqual({ kind: 'state', id: insertedState?.id });
  });

  test('keeps separate page instances isolated even when both use the same skill key', () => {
    const firstStore = createLoadedStore();
    const secondStore = createLoadedStore();

    act(() => {
      firstStore.getState().updateTaskState('intake', { title: '首个页面草稿' });
    });

    expect(firstStore.getState().document?.states.intake).toMatchObject({ title: '首个页面草稿' });
    expect(secondStore.getState().document?.states.intake).toMatchObject({ title: '收集上下文' });
  });

  test('addTaskBranch can create a fallback branch to a new handoff state and wire fallback policy to it', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addTaskBranch('intake', { transitionKind: 'fallback', targetKind: 'handoff' }, stubTaskBranchLabelsFallbackHandoff);
    });

    const state = store.getState();
    const fallbackTransition = Object.values(state.document?.transitions ?? {}).find(
      (transition) => transition.fromStateId === 'intake' && transition.kind === 'fallback',
    );

    expect(fallbackTransition).toBeDefined();
    expect(fallbackTransition?.toStateId).toContain('fallback');
    expect(state.document?.states[fallbackTransition?.toStateId ?? '']?.kind).toBe('handoff');

    const intakeState = state.document?.states.intake;
    expect(intakeState?.kind).toBe('task');
    if (intakeState?.kind !== 'task') {
      throw new Error('Expected intake to remain a task state.');
    }

    expect(intakeState.fallbackPolicy).toEqual({
      mode: 'goto',
      transitionId: fallbackTransition?.id ?? '',
      note: stubFallbackNote,
    });
  });

  test('deleteState removes a leaf branch state together with its incoming branch transition', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addTaskBranch('intake', { transitionKind: 'error', targetKind: 'terminal' }, stubTaskBranchLabelsError);
    });

    const branchTransition = Object.values(store.getState().document?.transitions ?? {}).find(
      (transition) => transition.fromStateId === 'intake' && transition.kind === 'error',
    );
    const leafStateId = branchTransition?.toStateId ?? '';

    expect(leafStateId).not.toBe('');

    act(() => {
      store.getState().deleteState(leafStateId);
    });

    const state = store.getState();

    expect(state.document?.states[leafStateId]).toBeUndefined();
    expect(
      Object.values(state.document?.transitions ?? {}).some((transition) => transition.toStateId === leafStateId),
    ).toBe(false);
  });

  test('updateToolPlanReason patches the selected tool reason without mutating other stores', () => {
    const store = createLoadedStore();

    act(() => {
      store.getState().addToolToTaskState('intake', 'query_refund_status');
      store.getState().updateToolPlanReason('intake', 'query_refund_status', '先读取退款状态，再决定后续路径。');
    });

    const state = store.getState();
    const intakeState = state.document?.states.intake;

    expect(intakeState?.kind).toBe('task');
    if (intakeState?.kind !== 'task') {
      throw new Error('Expected intake to remain a task state.');
    }

    expect(intakeState.toolPlan).toHaveLength(1);
    expect(intakeState.toolPlan[0].reason).toBe('先读取退款状态，再决定后续路径。');
  });
});
