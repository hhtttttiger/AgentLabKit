import { describe, expect, test } from 'vitest';
import type { SkillFlowDocument } from './types';
import { compileSkillFlow } from './compiler';

function buildFlow(): SkillFlowDocument {
  return {
    version: '3',
    metadata: {
      skillKey: 'refund-orchestration',
      displayName: 'Refund Orchestration',
      description: 'Refund routing flow',
      version: '1.0.0',
    },
    entryStateId: 'start',
    states: {
      start: { id: 'start', kind: 'start', title: 'Start' },
      intake: {
        id: 'intake',
        kind: 'task',
        title: 'Collect context',
        goal: 'Collect refund context',
        toolPlan: [],
        inputContract: { inherited: [], required: [], optional: [] },
        outputContract: [],
        fallbackPolicy: { mode: 'stay', note: 'Ask for more context' },
      },
      decision: { id: 'decision', kind: 'decision', title: 'Choose route', question: 'Which route?' },
      resolved: { id: 'resolved', kind: 'terminal', title: 'Resolved', outcome: 'resolved', resolutionNote: 'done' },
    },
    transitions: {
      'start-intake': { id: 'start-intake', fromStateId: 'start', toStateId: 'intake', label: 'Start', kind: 'default', priority: 0 },
      'intake-decision': { id: 'intake-decision', fromStateId: 'intake', toStateId: 'decision', label: 'Continue', kind: 'default', priority: 0 },
      'branch-b': {
        id: 'branch-b',
        fromStateId: 'decision',
        toStateId: 'resolved',
        label: 'Escalate',
        kind: 'handoff',
        priority: 1,
        predicate: { description: 'Escalation path', expression: { field: 'route', operator: 'eq', value: 'handoff' } },
      },
      'branch-a': {
        id: 'branch-a',
        fromStateId: 'decision',
        toStateId: 'resolved',
        label: 'Complete',
        kind: 'condition',
        priority: 0,
        predicate: { description: 'Default route', expression: { field: 'route', operator: 'eq', value: 'pass' } },
      },
    },
  };
}

describe('compileSkillFlow', () => {
  test('sorts outgoing transitions by priority and exposes incoming edges', () => {
    const compiled = compileSkillFlow(buildFlow());

    expect(compiled.entryStateId).toBe('start');
    expect(compiled.outgoingByStateId.decision.map((transition) => transition.id)).toEqual(['branch-a', 'branch-b']);
    expect(compiled.incomingByStateId.resolved.map((transition) => transition.id)).toEqual(['branch-b', 'branch-a']);
    expect(compiled.terminalStateIds).toEqual(['resolved']);
    expect(compiled.orderedBranchesByDecisionStateId.decision.map((transition) => transition.id)).toEqual(['branch-a', 'branch-b']);
    expect(compiled.validation.errors).toEqual([]);
  });
});
