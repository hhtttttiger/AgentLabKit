import type { CompiledSkillFlow, SkillFlowDocument, SkillFlowTransition } from './types';
import { validateSkillFlow } from './validateSkillFlow';

function sortByPriority(transitions: SkillFlowTransition[]) {
  return [...transitions].sort((a, b) => a.priority - b.priority);
}

export function compileSkillFlow(document: SkillFlowDocument): CompiledSkillFlow {
  const stateIds = Object.keys(document.states);
  const transitions = Object.values(document.transitions);
  const validation = validateSkillFlow(document);

  const outgoingByStateId = Object.fromEntries(
    stateIds.map((stateId) => [
      stateId,
      sortByPriority(transitions.filter((transition) => transition.fromStateId === stateId)),
    ]),
  );

  const incomingByStateId = Object.fromEntries(
    stateIds.map((stateId) => [
      stateId,
      transitions.filter((transition) => transition.toStateId === stateId),
    ]),
  );

  const terminalStateIds = stateIds.filter((stateId) => document.states[stateId].kind === 'terminal');
  const orderedBranchesByDecisionStateId = Object.fromEntries(
    stateIds
      .filter((stateId) => document.states[stateId].kind === 'decision')
      .map((stateId) => [stateId, outgoingByStateId[stateId] ?? []]),
  );

  return {
    document,
    entryStateId: document.entryStateId,
    outgoingByStateId,
    incomingByStateId,
    terminalStateIds,
    orderedBranchesByDecisionStateId,
    validation,
  };
}
