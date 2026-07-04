import { createContext, useContext, useRef, type PropsWithChildren } from 'react';
import { useStore } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { createStore, type StoreApi } from 'zustand/vanilla';
import type { Edge, Node, OnEdgesChange, OnNodesChange } from '@xyflow/react';
import { applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import { compileSkillFlow } from '../lib/compiler';
import { applyAutoLayoutToSkillFlow } from '../lib/layout';
import {
  graphStateToSkillFlowDocument,
  skillFlowDocumentToGraphState,
} from '../lib/reactFlowAdapters';
import type {
  BranchPredicate,
  CompiledSkillFlow,
  DecisionState,
  HandoffState,
  InputContract,
  OutputField,
  SkillFlowDocument,
  SkillFlowState,
  SkillFlowTransition,
  TaskState,
  TerminalState,
} from '../lib/types';

export type SkillFlowSelection =
  | { kind: 'state'; id: string }
  | { kind: 'transition'; id: string }
  | null;

export type TaskBranchDraft = {
  transitionKind: 'fallback' | 'error' | 'handoff';
  targetKind: 'terminal' | 'handoff';
};

export type WorkbenchNodeDefaults = {
  taskTitle: string;
  handoffTitle: string;
  handoffSummary: string;
  terminalTitle: string;
  terminalNote: string;
};

export type AddDecisionLabels = {
  decisionTitle: string;
  decisionQuestion: string;
  enterLabel: string;
  continueLabel: string;
  continueDescription: string;
  handoffBranchLabel: string;
  handoffTitle: string;
  handoffSummary: string;
};

export type AddBranchLabels = {
  handoffLabel: string;
  terminalLabel: string;
  conditionDescription: (n: number) => string;
  handoffTitle: string;
  handoffSummary: string;
  terminalTitle: string;
  terminalNote: string;
};

export type TaskBranchLabels = {
  handoff: string;
  fallbackHandoff: string;
  fallbackTerminal: string;
  errorHandoff: string;
  errorTerminal: string;
};

export type AddTaskBranchLabels = {
  transitionLabel: string;
  fallbackNote: string;
  handoffTitle: string;
  handoffSummary: string;
  terminalTitle: string;
  terminalNote: string;
};

export type SkillFlowBuilderState = {
  document: SkillFlowDocument | null;
  compiled: CompiledSkillFlow | null;
  nodes: Array<Node<SkillFlowState>>;
  edges: Array<Edge<SkillFlowTransition>>;
  selection: SkillFlowSelection;
  dirty: boolean;
  error: string | null;
  load: (document: SkillFlowDocument) => void;
  reset: () => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  setSelection: (selection: SkillFlowSelection) => void;
  addDecisionAfterState: (stateId: string, labels: AddDecisionLabels) => void;
  addTaskStateBeforeState: (stateId: string, taskTitle: string) => void;
  addTaskStateAfterState: (stateId: string, taskTitle: string) => void;
  addBranchToDecisionState: (stateId: string, targetKind: 'terminal' | 'handoff', labels: AddBranchLabels) => void;
  updateTaskState: (
    stateId: string,
    patch: Partial<Pick<TaskState, 'title' | 'goal' | 'inputContract' | 'outputContract' | 'fallbackPolicy'>>,
  ) => void;
  updateDecisionState: (
    stateId: string,
    patch: Partial<Pick<DecisionState, 'title' | 'question'>>,
  ) => void;
  updateHandoffState: (
    stateId: string,
    patch: Partial<Pick<HandoffState, 'title' | 'handoffType' | 'summaryTemplate'>>,
  ) => void;
  updateTerminalState: (
    stateId: string,
    patch: Partial<Pick<TerminalState, 'title' | 'outcome' | 'resolutionNote'>>,
  ) => void;
  updateTransition: (
    transitionId: string,
    patch: Partial<Pick<SkillFlowTransition, 'label' | 'kind' | 'priority' | 'predicate'>>,
  ) => void;
  addTaskBranch: (stateId: string, draft: TaskBranchDraft, labels: AddTaskBranchLabels) => void;
  deleteState: (stateId: string) => void;
  deleteTaskState: (stateId: string) => void;
  addToolToTaskState: (stateId: string, toolId: string, reason?: string) => void;
  removeToolFromTaskState: (stateId: string, toolId: string) => void;
  updateToolPlanReason: (stateId: string, toolId: string, reason: string) => void;
  applyLayout: (direction: 'TB' | 'LR') => void;
};

export type SkillFlowBuilderStore = StoreApi<SkillFlowBuilderState>;

export type SkillFlowBuilderStateSlice = Pick<
  SkillFlowBuilderState,
  'document' | 'compiled' | 'nodes' | 'edges' | 'selection' | 'dirty' | 'error'
>;

export type SkillFlowBuilderActions = Pick<
  SkillFlowBuilderState,
  | 'load'
  | 'reset'
  | 'setSelection'
  | 'onNodesChange'
  | 'onEdgesChange'
  | 'addTaskStateBeforeState'
  | 'addTaskStateAfterState'
  | 'addDecisionAfterState'
  | 'addBranchToDecisionState'
  | 'updateTaskState'
  | 'updateDecisionState'
  | 'updateHandoffState'
  | 'updateTerminalState'
  | 'updateTransition'
  | 'addTaskBranch'
  | 'deleteState'
  | 'addToolToTaskState'
  | 'removeToolFromTaskState'
  | 'updateToolPlanReason'
  | 'applyLayout'
>;

function getOutgoingTransitions(document: SkillFlowDocument, stateId: string) {
  return Object.values(document.transitions).filter((transition) => transition.fromStateId === stateId);
}

function getIncomingTransitions(document: SkillFlowDocument, stateId: string) {
  return Object.values(document.transitions).filter((transition) => transition.toStateId === stateId);
}

function getDecisionState(document: SkillFlowDocument, stateId: string): DecisionState | null {
  const state = document.states[stateId];
  return state?.kind === 'decision' ? state : null;
}

function getTaskState(document: SkillFlowDocument, stateId: string): TaskState | null {
  const state = document.states[stateId];
  return state?.kind === 'task' ? state : null;
}

function getTransition(document: SkillFlowDocument, transitionId: string): SkillFlowTransition | null {
  return document.transitions[transitionId] ?? null;
}

function getLeafState(document: SkillFlowDocument, stateId: string) {
  const state = document.states[stateId];
  if (!state || (state.kind !== 'handoff' && state.kind !== 'terminal')) {
    return null;
  }

  return state;
}

export function canInsertTaskStateAfter(document: SkillFlowDocument, stateId: string) {
  const state = document.states[stateId];
  if (!state || state.kind === 'terminal' || state.kind === 'handoff') {
    return false;
  }

  const outgoingTransitions = getOutgoingTransitions(document, stateId);
  return outgoingTransitions.length === 1 && outgoingTransitions[0]?.kind === 'default';
}

export function canInsertTaskStateBefore(document: SkillFlowDocument, stateId: string) {
  const state = document.states[stateId];
  if (!state || state.kind === 'start') {
    return false;
  }

  const incomingTransitions = getIncomingTransitions(document, stateId);
  return incomingTransitions.length === 1 && incomingTransitions[0]?.kind === 'default';
}

function materializeGraphState(document: SkillFlowDocument) {
  const graph = skillFlowDocumentToGraphState(document);
  const nodes = applyAutoLayoutToSkillFlow(graph.nodes, graph.edges, 'TB');
  return {
    nodes: nodes as Array<Node<SkillFlowState>>,
    edges: graph.edges as Array<Edge<SkillFlowTransition>>,
  };
}

function buildNextState(
  previousDocument: SkillFlowDocument,
  nodes: Array<Node<SkillFlowState>>,
  edges: Array<Edge<SkillFlowTransition>>,
) {
  const document = graphStateToSkillFlowDocument({
    nodes,
    edges,
    previousDocument,
  });
  const compiled = compileSkillFlow(document);

  return {
    document,
    compiled,
    error: compiled.validation.isValid ? null : compiled.validation.errors[0] ?? null,
  };
}

function hasMeaningfulNodeChanges(changes: Parameters<OnNodesChange>[0]) {
  return changes.some((change) => change.type !== 'dimensions' && change.type !== 'select');
}

function hasMeaningfulEdgeChanges(changes: Parameters<OnEdgesChange>[0]) {
  return changes.some((change) => change.type !== 'select');
}

function createDecisionId(existingIds: string[], stateId: string) {
  const baseId = `${stateId}-decision`;
  if (!existingIds.includes(baseId)) {
    return baseId;
  }

  let nextIndex = 2;
  while (existingIds.includes(`${baseId}-${nextIndex}`)) {
    nextIndex += 1;
  }
  return `${baseId}-${nextIndex}`;
}

function createTaskStateId(existingIds: string[], stateId: string) {
  const baseId = `${stateId}-task`;
  if (!existingIds.includes(baseId)) {
    return baseId;
  }

  let nextIndex = 2;
  while (existingIds.includes(`${baseId}-${nextIndex}`)) {
    nextIndex += 1;
  }
  return `${baseId}-${nextIndex}`;
}

function createBranchStateId(existingIds: string[], stateId: string, suffix: string) {
  const baseId = `${stateId}-${suffix}`;
  if (!existingIds.includes(baseId)) {
    return baseId;
  }

  let nextIndex = 2;
  while (existingIds.includes(`${baseId}-${nextIndex}`)) {
    nextIndex += 1;
  }
  return `${baseId}-${nextIndex}`;
}

function getDefaultOutgoingTransition(document: SkillFlowDocument, stateId: string) {
  return getOutgoingTransitions(document, stateId).find(
    (transition) => transition.fromStateId === stateId && transition.kind === 'default',
  );
}

function getDefaultIncomingTransition(document: SkillFlowDocument, stateId: string) {
  return getIncomingTransitions(document, stateId).find(
    (transition) => transition.toStateId === stateId && transition.kind === 'default',
  );
}

function insertStateAtPosition(
  states: SkillFlowDocument['states'],
  params: {
    insertId: string;
    insertState: SkillFlowState;
    relativeToId: string;
    position: 'before' | 'after';
  },
) {
  const nextStates: SkillFlowDocument['states'] = {};
  let inserted = false;

  for (const [stateId, state] of Object.entries(states)) {
    if (!inserted && params.position === 'before' && stateId === params.relativeToId) {
      nextStates[params.insertId] = params.insertState;
      inserted = true;
    }

    nextStates[stateId] = state;

    if (!inserted && params.position === 'after' && stateId === params.relativeToId) {
      nextStates[params.insertId] = params.insertState;
      inserted = true;
    }
  }

  if (!inserted) {
    nextStates[params.insertId] = params.insertState;
  }

  return nextStates;
}

function getInitialSelection(document: SkillFlowDocument): SkillFlowSelection {
  const entryTransition = getDefaultOutgoingTransition(document, document.entryStateId);
  const entryTargetState = entryTransition ? document.states[entryTransition.toStateId] : null;

  if (entryTargetState && entryTargetState.kind !== 'start') {
    return { kind: 'state', id: entryTargetState.id };
  }

  const firstEditableState = Object.values(document.states).find((state) => state.kind !== 'start');
  return firstEditableState
    ? { kind: 'state', id: firstEditableState.id }
    : { kind: 'state', id: document.entryStateId };
}

function buildEmptyTaskState(stateId: string, title: string): TaskState {
  return {
    id: stateId,
    kind: 'task',
    title,
    goal: '',
    toolPlan: [],
    inputContract: {
      inherited: [],
      required: [],
      optional: [],
    },
    outputContract: [],
    fallbackPolicy: {
      mode: 'stay',
      note: '',
    },
  };
}

function buildEmptyHandoffState(stateId: string, title: string, summaryTemplate: string): HandoffState {
  return {
    id: stateId,
    kind: 'handoff',
    title,
    handoffType: 'human',
    summaryTemplate,
  };
}

function buildEmptyTerminalState(stateId: string, title: string, resolutionNote: string): TerminalState {
  return {
    id: stateId,
    kind: 'terminal',
    title,
    outcome: 'resolved',
    resolutionNote,
  };
}

function cloneInputContract(contract: InputContract): InputContract {
  return {
    inherited: contract.inherited.map((field) => ({ ...field })),
    required: contract.required.map((field) => ({ ...field })),
    optional: contract.optional.map((field) => ({ ...field })),
  };
}

function cloneOutputContract(contract: OutputField[]): OutputField[] {
  return contract.map((field) => ({ ...field }));
}

function clonePredicate(predicate: BranchPredicate | undefined) {
  if (!predicate) {
    return undefined;
  }

  return predicate.expression.operator === 'in'
    ? {
        ...predicate,
        expression: {
          ...predicate.expression,
          value: [...predicate.expression.value],
        },
      }
    : {
        ...predicate,
        expression: { ...predicate.expression },
    };
}

const emptyState = {
  document: null,
  compiled: null,
  nodes: [] as Array<Node<SkillFlowState>>,
  edges: [] as Array<Edge<SkillFlowTransition>>,
  selection: null as SkillFlowSelection,
  dirty: false,
  error: null as string | null,
};

export function createSkillFlowBuilderStore(): SkillFlowBuilderStore {
  return createStore<SkillFlowBuilderState>((set, get) => ({
    ...emptyState,

    load(document) {
      const compiled = compileSkillFlow(document);
      const graphState = materializeGraphState(document);

      set({
        document,
        compiled,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: getInitialSelection(document),
        dirty: false,
        error: compiled.validation.isValid ? null : compiled.validation.errors[0] ?? null,
      });
    },

    reset() {
      set(emptyState);
    },

    onNodesChange(changes) {
      const currentDocument = get().document;
      if (!currentDocument) {
        return;
      }

      const nextNodes = applyNodeChanges(changes, get().nodes) as Array<Node<SkillFlowState>>;

      if (!hasMeaningfulNodeChanges(changes)) {
        set({ nodes: nextNodes });
        return;
      }

      const next = buildNextState(currentDocument, nextNodes, get().edges);
      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    onEdgesChange(changes) {
      const currentDocument = get().document;
      if (!currentDocument) {
        return;
      }

      const nextEdges = applyEdgeChanges(changes, get().edges) as Array<Edge<SkillFlowTransition>>;

      if (!hasMeaningfulEdgeChanges(changes)) {
        set({ edges: nextEdges });
        return;
      }

      const next = buildNextState(currentDocument, get().nodes, nextEdges);
      set({
        ...next,
        edges: nextEdges,
        dirty: true,
      });
    },

    setSelection(selection) {
      set({ selection });
    },

    addDecisionAfterState(stateId, labels) {
      const currentDocument = get().document;
      if (!currentDocument || !canInsertTaskStateAfter(currentDocument, stateId)) {
        return;
      }

      const stateToReplace = getDefaultOutgoingTransition(currentDocument, stateId);
      if (!stateToReplace) {
        return;
      }

      const existingStateIds = Object.keys(currentDocument.states);
      const decisionId = createDecisionId(existingStateIds, stateId);
      const handoffId = createBranchStateId(existingStateIds, decisionId, 'handoff');

      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: insertStateAtPosition(
          insertStateAtPosition(currentDocument.states, {
            insertId: decisionId,
            insertState: {
              id: decisionId,
              kind: 'decision',
              title: labels.decisionTitle,
              question: labels.decisionQuestion,
            },
            relativeToId: stateId,
            position: 'after',
          }),
          {
            insertId: handoffId,
            insertState: buildEmptyHandoffState(handoffId, labels.handoffTitle, labels.handoffSummary),
            relativeToId: decisionId,
            position: 'after',
          },
        ),
        transitions: {
          ...currentDocument.transitions,
          [stateToReplace.id]: {
            ...stateToReplace,
            toStateId: decisionId,
            label: labels.enterLabel,
          },
          [`${decisionId}-${stateToReplace.toStateId}`]: {
            id: `${decisionId}-${stateToReplace.toStateId}`,
            fromStateId: decisionId,
            toStateId: stateToReplace.toStateId,
            label: labels.continueLabel,
            kind: 'condition',
            priority: 0,
            predicate: {
              description: labels.continueDescription,
              expression: { field: 'route', operator: 'eq', value: 'auto' },
            },
          },
          [`${decisionId}-${handoffId}`]: {
            id: `${decisionId}-${handoffId}`,
            fromStateId: decisionId,
            toStateId: handoffId,
            label: labels.handoffBranchLabel,
            kind: 'handoff',
            priority: 1,
          },
        },
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'state', id: decisionId },
        dirty: true,
      });
    },

    addTaskStateAfterState(stateId, taskTitle) {
      const currentDocument = get().document;
      if (!currentDocument || !canInsertTaskStateAfter(currentDocument, stateId)) {
        return;
      }

      const stateToReplace = getDefaultOutgoingTransition(currentDocument, stateId);
      if (!stateToReplace) {
        return;
      }

      const taskId = createTaskStateId(Object.keys(currentDocument.states), stateId);
      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: insertStateAtPosition(currentDocument.states, {
          insertId: taskId,
          insertState: buildEmptyTaskState(taskId, taskTitle),
          relativeToId: stateId,
          position: 'after',
        }),
        transitions: {
          ...currentDocument.transitions,
          [stateToReplace.id]: {
            ...stateToReplace,
            toStateId: taskId,
          },
          [`${taskId}-${stateToReplace.toStateId}`]: {
            id: `${taskId}-${stateToReplace.toStateId}`,
            fromStateId: taskId,
            toStateId: stateToReplace.toStateId,
            label: stateToReplace.label,
            kind: 'default',
            priority: 0,
          },
        },
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'state', id: taskId },
        dirty: true,
      });
    },

    addTaskStateBeforeState(stateId, taskTitle) {
      const currentDocument = get().document;
      if (!currentDocument || !canInsertTaskStateBefore(currentDocument, stateId)) {
        return;
      }

      const stateToReplace = getDefaultIncomingTransition(currentDocument, stateId);
      if (!stateToReplace) {
        return;
      }

      const taskId = createTaskStateId(Object.keys(currentDocument.states), stateId);
      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: insertStateAtPosition(currentDocument.states, {
          insertId: taskId,
          insertState: buildEmptyTaskState(taskId, taskTitle),
          relativeToId: stateId,
          position: 'before',
        }),
        transitions: {
          ...currentDocument.transitions,
          [stateToReplace.id]: {
            ...stateToReplace,
            toStateId: taskId,
          },
          [`${taskId}-${stateId}`]: {
            id: `${taskId}-${stateId}`,
            fromStateId: taskId,
            toStateId: stateId,
            label: stateToReplace.label,
            kind: 'default',
            priority: 0,
          },
        },
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'state', id: taskId },
        dirty: true,
      });
    },

    addBranchToDecisionState(stateId, targetKind, labels) {
      const currentDocument = get().document;
      const decisionState = currentDocument ? getDecisionState(currentDocument, stateId) : null;
      if (!currentDocument || !decisionState) {
        return;
      }

      const existingStateIds = Object.keys(currentDocument.states);
      const targetId = createBranchStateId(existingStateIds, stateId, targetKind);
      const branchPriority = getOutgoingTransitions(currentDocument, stateId).reduce(
        (maxPriority, transition) => Math.max(maxPriority, transition.priority),
        -1,
      ) + 1;

      const branchTransitionId = `${stateId}-${targetId}`;
      const branchTransition: SkillFlowTransition = {
        id: branchTransitionId,
        fromStateId: stateId,
        toStateId: targetId,
        label: targetKind === 'handoff' ? labels.handoffLabel : labels.terminalLabel,
        kind: targetKind === 'handoff' ? 'handoff' : 'condition',
        priority: branchPriority,
        predicate: targetKind === 'handoff'
          ? undefined
          : {
              description: labels.conditionDescription(branchPriority + 1),
              expression: {
                field: 'route',
                operator: 'eq',
                value: `branch_${branchPriority + 1}`,
              },
            },
      };

      const targetState = targetKind === 'handoff'
        ? buildEmptyHandoffState(targetId, labels.handoffTitle, labels.handoffSummary)
        : buildEmptyTerminalState(targetId, labels.terminalTitle, labels.terminalNote);

      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: insertStateAtPosition(currentDocument.states, {
          insertId: targetId,
          insertState: targetState,
          relativeToId: stateId,
          position: 'after',
        }),
        transitions: {
          ...currentDocument.transitions,
          [branchTransitionId]: branchTransition,
        },
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'transition', id: branchTransitionId },
        dirty: true,
      });
    },

    updateTaskState(stateId, patch) {
      const currentDocument = get().document;
      const taskState = currentDocument ? getTaskState(currentDocument, stateId) : null;
      if (!currentDocument || !taskState) {
        return;
      }

      const nextTaskState: TaskState = {
        ...taskState,
        ...patch,
        inputContract: patch.inputContract ? cloneInputContract(patch.inputContract) : taskState.inputContract,
        outputContract: patch.outputContract ? cloneOutputContract(patch.outputContract) : taskState.outputContract,
        fallbackPolicy: patch.fallbackPolicy ? { ...patch.fallbackPolicy } : taskState.fallbackPolicy,
      };

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? { ...node, data: nextTaskState }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    updateDecisionState(stateId, patch) {
      const currentDocument = get().document;
      const decisionState = currentDocument ? getDecisionState(currentDocument, stateId) : null;
      if (!currentDocument || !decisionState) {
        return;
      }

      const nextDecisionState: DecisionState = {
        ...decisionState,
        ...patch,
      };

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? { ...node, data: nextDecisionState }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    updateHandoffState(stateId, patch) {
      const currentDocument = get().document;
      const state = currentDocument?.states[stateId];
      if (!currentDocument || state?.kind !== 'handoff') {
        return;
      }

      const nextState: HandoffState = {
        ...state,
        ...patch,
      };

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? { ...node, data: nextState }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    updateTerminalState(stateId, patch) {
      const currentDocument = get().document;
      const state = currentDocument?.states[stateId];
      if (!currentDocument || state?.kind !== 'terminal') {
        return;
      }

      const nextState: TerminalState = {
        ...state,
        ...patch,
      };

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? { ...node, data: nextState }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    updateTransition(transitionId, patch) {
      const currentDocument = get().document;
      const transition = currentDocument ? getTransition(currentDocument, transitionId) : null;
      if (!currentDocument || !transition) {
        return;
      }

      const nextTransition: SkillFlowTransition = {
        ...transition,
        ...patch,
        predicate: patch.predicate === undefined
          ? transition.predicate
          : clonePredicate(patch.predicate),
      };

      const nextEdges = get().edges.map((edge) =>
        edge.id === transitionId
          ? {
              ...edge,
              label: nextTransition.label,
              data: nextTransition,
            }
          : edge,
      );
      const next = buildNextState(currentDocument, get().nodes, nextEdges);

      set({
        ...next,
        edges: nextEdges,
        dirty: true,
      });
    },

    addTaskBranch(stateId, draft, labels) {
      const currentDocument = get().document;
      const taskState = currentDocument ? getTaskState(currentDocument, stateId) : null;
      if (!currentDocument || !taskState) {
        return;
      }

      if (draft.transitionKind === 'handoff' && draft.targetKind !== 'handoff') {
        return;
      }

      const existingSibling = getOutgoingTransitions(currentDocument, stateId).find(
        (transition) => transition.kind === draft.transitionKind,
      );

      if (existingSibling) {
        return;
      }

      const existingStateIds = Object.keys(currentDocument.states);
      const targetId = createBranchStateId(existingStateIds, stateId, draft.transitionKind);
      const nextPriority = getOutgoingTransitions(currentDocument, stateId).reduce(
        (maxPriority, transition) => Math.max(maxPriority, transition.priority),
        -1,
      ) + 1;
      const transitionId = `${stateId}-${targetId}`;
      const nextTaskState: TaskState = draft.transitionKind === 'fallback'
        ? {
            ...taskState,
            fallbackPolicy: {
              mode: 'goto',
              transitionId,
              note: labels.fallbackNote,
            },
          }
        : { ...taskState };
      const targetState = draft.targetKind === 'handoff'
        ? buildEmptyHandoffState(targetId, labels.handoffTitle, labels.handoffSummary)
        : buildEmptyTerminalState(targetId, labels.terminalTitle, labels.terminalNote);

      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: insertStateAtPosition(
          {
            ...currentDocument.states,
            [stateId]: nextTaskState,
          },
          {
            insertId: targetId,
            insertState: targetState,
            relativeToId: stateId,
            position: 'after',
          },
        ),
        transitions: {
          ...currentDocument.transitions,
          [transitionId]: {
            id: transitionId,
            fromStateId: stateId,
            toStateId: targetId,
            label: labels.transitionLabel,
            kind: draft.transitionKind,
            priority: nextPriority,
          },
        },
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'transition', id: transitionId },
        dirty: true,
      });
    },

    deleteState(stateId) {
      const currentDocument = get().document;
      if (!currentDocument) {
        return;
      }

      if (getTaskState(currentDocument, stateId)) {
        get().deleteTaskState(stateId);
        return;
      }

      if (!getLeafState(currentDocument, stateId)) {
        return;
      }

      const incomingTransitions = getIncomingTransitions(currentDocument, stateId);
      const outgoingTransitions = getOutgoingTransitions(currentDocument, stateId);
      if (outgoingTransitions.length > 0) {
        return;
      }

      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: Object.fromEntries(
          Object.entries(currentDocument.states).filter(([candidateStateId]) => candidateStateId !== stateId),
        ),
        transitions: Object.fromEntries(
          Object.entries(currentDocument.transitions).filter(([, transition]) =>
            transition.fromStateId !== stateId && transition.toStateId !== stateId),
        ),
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);
      const nextSelectedStateId = incomingTransitions[0]?.fromStateId ?? currentDocument.entryStateId;

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'state', id: nextSelectedStateId },
        dirty: true,
      });
    },

    deleteTaskState(stateId) {
      const currentDocument = get().document;
      if (!currentDocument) {
        return;
      }

      const taskState = getTaskState(currentDocument, stateId);
      if (!taskState) {
        return;
      }

      const connectedTransitions = Object.values(currentDocument.transitions).filter(
        (transition) => transition.fromStateId === stateId || transition.toStateId === stateId,
      );
      const incomingTransitions = connectedTransitions.filter((transition) => transition.toStateId === stateId);
      const outgoingTransitions = connectedTransitions.filter((transition) => transition.fromStateId === stateId);

      const nextTransitions = Object.fromEntries(
        Object.entries(currentDocument.transitions).filter(([transitionId]) =>
          !connectedTransitions.some((transition) => transition.id === transitionId),
        ),
      );

      if (incomingTransitions.length === 1 && outgoingTransitions.length === 1) {
        const [incomingTransition] = incomingTransitions;
        const [outgoingTransition] = outgoingTransitions;

        nextTransitions[incomingTransition.id] = {
          ...incomingTransition,
          toStateId: outgoingTransition.toStateId,
          label: outgoingTransition.label,
        };
      }

      const nextDocument: SkillFlowDocument = {
        ...currentDocument,
        states: Object.fromEntries(
          Object.entries(currentDocument.states).filter(([candidateStateId]) => candidateStateId !== stateId),
        ),
        transitions: nextTransitions,
      };

      const graphState = materializeGraphState(nextDocument);
      const next = buildNextState(nextDocument, graphState.nodes, graphState.edges);
      const nextSelectedStateId = incomingTransitions[0]?.fromStateId ?? currentDocument.entryStateId;

      set({
        ...next,
        nodes: graphState.nodes,
        edges: graphState.edges,
        selection: { kind: 'state', id: nextSelectedStateId },
        dirty: true,
      });
    },

    addToolToTaskState(stateId, toolId, reason) {
      const currentDocument = get().document;
      const taskState = currentDocument ? getTaskState(currentDocument, stateId) : null;
      if (!currentDocument || !taskState || taskState.toolPlan.some((plan) => plan.toolId === toolId)) {
        return;
      }

      const nextTaskState: TaskState = {
        ...taskState,
        toolPlan: [
          ...taskState.toolPlan,
          {
            id: `${stateId}-${toolId}-${taskState.toolPlan.length + 1}`,
            toolId,
            reason: reason ?? '',
          },
        ],
      };

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? { ...node, data: nextTaskState }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    removeToolFromTaskState(stateId, toolId) {
      const currentDocument = get().document;
      const taskState = currentDocument ? getTaskState(currentDocument, stateId) : null;
      if (!currentDocument || !taskState) {
        return;
      }

      const nextToolPlan = taskState.toolPlan.filter((plan) => plan.toolId !== toolId);
      if (nextToolPlan.length === taskState.toolPlan.length) {
        return;
      }

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? {
              ...node,
              data: {
                ...taskState,
                toolPlan: nextToolPlan,
              },
            }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    updateToolPlanReason(stateId, toolId, reason) {
      const currentDocument = get().document;
      const taskState = currentDocument ? getTaskState(currentDocument, stateId) : null;
      if (!currentDocument || !taskState) {
        return;
      }

      const nextToolPlan = taskState.toolPlan.map((plan) =>
        plan.toolId === toolId
          ? { ...plan, reason }
          : plan,
      );
      if (nextToolPlan.every((plan, index) => plan.reason === taskState.toolPlan[index]?.reason)) {
        return;
      }

      const nextNodes = get().nodes.map((node) =>
        node.id === stateId
          ? {
              ...node,
              data: {
                ...taskState,
                toolPlan: nextToolPlan,
              },
            }
          : node,
      );
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },

    applyLayout(direction) {
      const currentDocument = get().document;
      if (!currentDocument) {
        return;
      }

      const nextNodes = applyAutoLayoutToSkillFlow(get().nodes, get().edges, direction);
      const next = buildNextState(currentDocument, nextNodes, get().edges);

      set({
        ...next,
        nodes: nextNodes,
        dirty: true,
      });
    },
  }));
}

const SkillFlowBuilderStoreContext = createContext<SkillFlowBuilderStore | null>(null);

export function SkillFlowBuilderStoreProvider({ children }: PropsWithChildren) {
  const storeRef = useRef<SkillFlowBuilderStore | null>(null);
  if (!storeRef.current) {
    storeRef.current = createSkillFlowBuilderStore();
  }

  return (
    <SkillFlowBuilderStoreContext.Provider value={storeRef.current}>
      {children}
    </SkillFlowBuilderStoreContext.Provider>
  );
}

export function useSkillFlowBuilderStore<T>(selector: (state: SkillFlowBuilderState) => T) {
  const store = useContext(SkillFlowBuilderStoreContext);
  if (!store) {
    throw new Error('useSkillFlowBuilderStore must be used within SkillFlowBuilderStoreProvider.');
  }

  return useStore(store, selector);
}

export function useSkillFlowBuilderStoreShallow<T extends object>(selector: (state: SkillFlowBuilderState) => T) {
  return useSkillFlowBuilderStore(useShallow(selector));
}

export function useSkillFlowBuilderState() {
  return useSkillFlowBuilderStoreShallow((state): SkillFlowBuilderStateSlice => ({
    document: state.document,
    compiled: state.compiled,
    nodes: state.nodes,
    edges: state.edges,
    selection: state.selection,
    dirty: state.dirty,
    error: state.error,
  }));
}

export function useSkillFlowBuilderActions() {
  return useSkillFlowBuilderStoreShallow((state): SkillFlowBuilderActions => ({
    load: state.load,
    reset: state.reset,
    setSelection: state.setSelection,
    onNodesChange: state.onNodesChange,
    onEdgesChange: state.onEdgesChange,
    addTaskStateBeforeState: state.addTaskStateBeforeState,
    addTaskStateAfterState: state.addTaskStateAfterState,
    addDecisionAfterState: state.addDecisionAfterState,
    addBranchToDecisionState: state.addBranchToDecisionState,
    updateTaskState: state.updateTaskState,
    updateDecisionState: state.updateDecisionState,
    updateHandoffState: state.updateHandoffState,
    updateTerminalState: state.updateTerminalState,
    updateTransition: state.updateTransition,
    addTaskBranch: state.addTaskBranch,
    deleteState: state.deleteState,
    addToolToTaskState: state.addToolToTaskState,
    removeToolFromTaskState: state.removeToolFromTaskState,
    updateToolPlanReason: state.updateToolPlanReason,
    applyLayout: state.applyLayout,
  }));
}

export function useSkillFlowBuilderStoreApi() {
  const store = useContext(SkillFlowBuilderStoreContext);
  if (!store) {
    throw new Error('useSkillFlowBuilderStoreApi must be used within SkillFlowBuilderStoreProvider.');
  }

  return store;
}
