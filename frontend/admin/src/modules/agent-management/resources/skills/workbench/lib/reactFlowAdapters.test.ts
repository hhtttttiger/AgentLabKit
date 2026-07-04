import { describe, expect, test } from 'vitest';
import { graphStateToSkillFlowDocument, skillFlowDocumentToGraphState } from './reactFlowAdapters';
import type { SkillFlowDocument } from './types';

const flow: SkillFlowDocument = {
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
    decision: { id: 'decision', kind: 'decision', title: 'Choose route', question: 'Which route?' },
    done: { id: 'done', kind: 'terminal', title: 'Done', outcome: 'resolved', resolutionNote: 'Finished' },
  },
  transitions: {
    'start-decision': { id: 'start-decision', fromStateId: 'start', toStateId: 'decision', label: 'Start', kind: 'default', priority: 0 },
    'branch-status': {
      id: 'branch-status',
      fromStateId: 'decision',
      toStateId: 'done',
      label: 'Check status',
      kind: 'condition',
      priority: 0,
      predicate: { description: 'Status branch', expression: { field: 'intent_type', operator: 'eq', value: 'status' } },
    },
    'branch-ticket': {
      id: 'branch-ticket',
      fromStateId: 'decision',
      toStateId: 'done',
      label: 'Create ticket',
      kind: 'condition',
      priority: 1,
      predicate: { description: 'Execution branch', expression: { field: 'intent_type', operator: 'eq', value: 'execute' } },
    },
  },
};

describe('reactFlowAdapters', () => {
  test('round-trips branch labels, priorities, predicates, and positions through graph state', () => {
    const graph = skillFlowDocumentToGraphState(flow, {
      start: { x: 10, y: 20 },
      decision: { x: 30, y: 40 },
      done: { x: 50, y: 60 },
    });

    expect(graph.nodes.map((node) => node.position)).toEqual([
      { x: 10, y: 20 },
      { x: 30, y: 40 },
      { x: 50, y: 60 },
    ]);

    const movedNodes = graph.nodes.map((node) =>
      node.id === 'decision' ? { ...node, position: { x: 90, y: 120 } } : node,
    );

    const roundTripped = graphStateToSkillFlowDocument({
      nodes: movedNodes,
      edges: graph.edges,
      previousDocument: flow,
    });

    expect(roundTripped.transitions['branch-status'].label).toBe('Check status');
    expect(roundTripped.transitions['branch-ticket'].priority).toBe(1);
    expect(roundTripped.transitions['branch-ticket'].predicate?.description).toBe('Execution branch');
    expect(roundTripped.states.decision.title).toBe('Choose route');
  });
});
