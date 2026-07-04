import type { Edge, Node } from '@xyflow/react';
import type {
  BranchPredicate,
  PredicateAst,
  SkillFlowDocument,
  SkillFlowState,
  SkillFlowTransition,
} from './types';

export type SkillFlowGraphNode = Node<SkillFlowState>;
export type SkillFlowGraphEdge = Edge<SkillFlowTransition>;

function cloneState(state: SkillFlowState): SkillFlowState {
  if (state.kind === 'task') {
    return {
      ...state,
      toolPlan: state.toolPlan.map((plan) => ({ ...plan })),
      inputContract: {
        inherited: state.inputContract.inherited.map((field) => ({ ...field })),
        required: state.inputContract.required.map((field) => ({ ...field })),
        optional: state.inputContract.optional.map((field) => ({ ...field })),
      },
      outputContract: state.outputContract.map((field) => ({ ...field })),
      fallbackPolicy: { ...state.fallbackPolicy },
    };
  }

  return { ...state };
}

function cloneTransition(transition: SkillFlowTransition): SkillFlowTransition {
  const clonePredicate = (predicate: BranchPredicate): BranchPredicate => {
    const expression: PredicateAst = predicate.expression.operator === 'in'
      ? { ...predicate.expression, value: [...predicate.expression.value] }
      : { ...predicate.expression };

    return {
      ...predicate,
      expression,
    };
  };

  return {
    ...transition,
    predicate: transition.predicate ? clonePredicate(transition.predicate) : undefined,
  };
}

export function skillFlowDocumentToGraphState(
  document: SkillFlowDocument,
  nodePositions: Record<string, { x: number; y: number }> = {},
): { nodes: SkillFlowGraphNode[]; edges: SkillFlowGraphEdge[] } {
  return {
    nodes: Object.values(document.states).map((state) => ({
      id: state.id,
      type: state.kind,
      position: nodePositions[state.id] ?? { x: 0, y: 0 },
      data: cloneState(state),
    })),
    edges: Object.values(document.transitions).map((transition) => ({
      id: transition.id,
      source: transition.fromStateId,
      target: transition.toStateId,
      label: transition.label,
      data: cloneTransition(transition),
    })),
  };
}

export function graphStateToSkillFlowDocument(params: {
  nodes: SkillFlowGraphNode[];
  edges: SkillFlowGraphEdge[];
  previousDocument: SkillFlowDocument;
}): SkillFlowDocument {
  return {
    ...params.previousDocument,
    states: Object.fromEntries(params.nodes.map((node) => [node.id, cloneState(node.data)])),
    transitions: Object.fromEntries(
      params.edges.map((edge) => [
        edge.id,
        cloneTransition(
          edge.data ?? {
            id: edge.id,
            fromStateId: edge.source,
            toStateId: edge.target,
            label: typeof edge.label === 'string' ? edge.label : '',
            kind: 'default',
            priority: 0,
          },
        ),
      ]),
    ),
  };
}
