import type {
  DecisionState,
  SkillFlowDocument,
  SkillFlowState,
  SkillFlowTransition,
  SkillFlowValidationResult,
  TaskState,
} from './types';

function isDecisionState(state: SkillFlowState): state is DecisionState {
  return state.kind === 'decision';
}

function isTaskState(state: SkillFlowState): state is TaskState {
  return state.kind === 'task';
}

function getOutgoingTransitions(flow: SkillFlowDocument, stateId: string): SkillFlowTransition[] {
  return Object.values(flow.transitions).filter((transition) => transition.fromStateId === stateId);
}

function getTransitionsByKind(transitions: SkillFlowTransition[], kind: SkillFlowTransition['kind']) {
  return transitions.filter((transition) => transition.kind === kind);
}

function hasState(flow: SkillFlowDocument, stateId: string) {
  return Object.hasOwn(flow.states, stateId);
}

function hasTransition(flow: SkillFlowDocument, transitionId: string) {
  return Object.hasOwn(flow.transitions, transitionId);
}

export function validateSkillFlow(flow: SkillFlowDocument): SkillFlowValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const states = Object.values(flow.states);
  const transitions = Object.values(flow.transitions);

  if (!hasState(flow, flow.entryStateId)) {
    errors.push(`入口节点 "${flow.entryStateId}" 不存在。`);
  } else if (flow.states[flow.entryStateId].kind !== 'start') {
    errors.push(`入口节点 "${flow.entryStateId}" 必须指向开始节点。`);
  }

  const startStates = states.filter((state) => state.kind === 'start');
  if (startStates.length !== 1) {
    errors.push(`技能编排必须包含且仅包含 1 个开始节点，当前为 ${startStates.length} 个。`);
  }

  for (const transition of transitions) {
    if (!hasState(flow, transition.fromStateId)) {
      errors.push(`流转 "${transition.id}" 指向了不存在的来源节点 "${transition.fromStateId}"。`);
    }
    if (!hasState(flow, transition.toStateId)) {
      errors.push(`流转 "${transition.id}" 指向了不存在的目标节点 "${transition.toStateId}"。`);
    }
  }

  for (const state of states) {
    const outgoing = getOutgoingTransitions(flow, state.id);
    const defaultOutgoing = getTransitionsByKind(outgoing, 'default');
    const fallbackOutgoing = getTransitionsByKind(outgoing, 'fallback');
    const handoffOutgoing = getTransitionsByKind(outgoing, 'handoff');
    const errorOutgoing = getTransitionsByKind(outgoing, 'error');

    if (state.kind === 'terminal' && outgoing.length > 0) {
      errors.push(`结束节点 "${state.id}" 不能再有外出流转。`);
    }

    if (state.kind === 'handoff' && outgoing.length > 0) {
      errors.push(`转交节点 "${state.id}" 不能再有外出流转。`);
    }

    if (state.kind === 'start') {
      if (defaultOutgoing.length !== 1 || outgoing.length !== 1) {
        errors.push(`开始节点 "${state.id}" 必须且只能有 1 条默认流转。`);
      }
    }

    if (state.kind === 'task') {
      if (defaultOutgoing.length !== 1) {
        errors.push(`任务节点 "${state.id}" 必须保留 1 条默认流转。`);
      }

      if (fallbackOutgoing.length > 1) {
        errors.push(`任务节点 "${state.id}" 只能保留 1 条 fallback 兜底流转。`);
      }

      if (handoffOutgoing.length > 1) {
        errors.push(`任务节点 "${state.id}" 只能保留 1 条 handoff 转交流转。`);
      }

      if (errorOutgoing.length > 1) {
        errors.push(`任务节点 "${state.id}" 只能保留 1 条 error 异常流转。`);
      }
    }

    if (isDecisionState(state)) {
      if (outgoing.length < 2) {
        errors.push(`判断节点 "${state.id}" 至少需要 2 条外出流转。`);
      }

      const seenPriorities = new Set<number>();
      for (const transition of outgoing) {
        if (transition.kind !== 'condition' && transition.kind !== 'handoff') {
          errors.push(`判断节点 "${state.id}" 的流转 "${transition.id}" 只能使用 condition 或 handoff 类型。`);
        }
        if (seenPriorities.has(transition.priority)) {
          errors.push(`判断节点 "${state.id}" 存在重复的流转优先级 "${transition.priority}"。`);
        }
        seenPriorities.add(transition.priority);

        if (transition.kind === 'condition' && !transition.predicate) {
          errors.push(`判断节点 "${state.id}" 的条件流转 "${transition.id}" 必须配置命中条件。`);
        }
      }
    }

    if (isTaskState(state) && state.fallbackPolicy.mode === 'goto') {
      if (!hasTransition(flow, state.fallbackPolicy.transitionId)) {
        errors.push(`任务节点 "${state.id}" 的 goto 兜底流转 "${state.fallbackPolicy.transitionId}" 不存在。`);
      } else {
        const fallbackTransition = flow.transitions[state.fallbackPolicy.transitionId];
        if (fallbackTransition.fromStateId !== state.id || fallbackTransition.kind !== 'fallback') {
          errors.push(
            `任务节点 "${state.id}" 的 goto 兜底流转 "${state.fallbackPolicy.transitionId}" 必须是当前节点发出的 fallback 流转。`,
          );
        }
      }
    }

    if (isTaskState(state) && state.fallbackPolicy.mode === 'handoff' && handoffOutgoing.length === 0) {
      errors.push(`任务节点 "${state.id}" 选择“转交处理”兜底时，必须配置 1 条 handoff 流转。`);
    }
  }

  const visited = new Set<string>();
  const queue = [flow.entryStateId];

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || visited.has(current) || !hasState(flow, current)) {
      continue;
    }

    visited.add(current);
    for (const transition of getOutgoingTransitions(flow, current)) {
      queue.push(transition.toStateId);
    }
  }

  for (const state of states) {
    if (!visited.has(state.id)) {
      errors.push(`节点 "${state.id}" 无法从入口节点 "${flow.entryStateId}" 到达。`);
    }
  }

  return { isValid: errors.length === 0, errors, warnings };
}
