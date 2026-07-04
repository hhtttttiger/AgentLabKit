export type PredicateAst =
  | { field: string; operator: 'eq'; value: string }
  | { field: string; operator: 'in'; value: string[] };

export type SkillFlowStateKind = 'start' | 'task' | 'decision' | 'handoff' | 'terminal';
export type SkillFlowTransitionKind = 'default' | 'condition' | 'fallback' | 'error' | 'handoff';

export type SkillFlowMetadata = {
  skillKey: string;
  displayName: string;
  description: string;
  version: string;
};

export type ToolInvocationPlan = {
  id: string;
  toolId: string;
  reason: string;
};

export type InputField = {
  key: string;
  label: string;
};

export type InputContract = {
  inherited: InputField[];
  required: InputField[];
  optional: InputField[];
};

export type OutputField = {
  key: string;
  label: string;
};

export type FallbackPolicy =
  | { mode: 'stay'; note: string }
  | { mode: 'handoff'; note: string }
  | { mode: 'goto'; transitionId: string; note: string };

export type BranchPredicate = {
  expression: PredicateAst;
  description: string;
};

export type StartState = { id: string; kind: 'start'; title: string };

export type TaskState = {
  id: string;
  kind: 'task';
  title: string;
  goal: string;
  toolPlan: ToolInvocationPlan[];
  inputContract: InputContract;
  outputContract: OutputField[];
  fallbackPolicy: FallbackPolicy;
};

export type DecisionState = {
  id: string;
  kind: 'decision';
  title: string;
  question: string;
};

export type HandoffState = {
  id: string;
  kind: 'handoff';
  title: string;
  handoffType: 'human' | 'ticket' | 'other_agent';
  summaryTemplate: string;
};

export type TerminalState = {
  id: string;
  kind: 'terminal';
  title: string;
  outcome: 'resolved' | 'blocked' | 'cancelled';
  resolutionNote: string;
};

export type SkillFlowState = StartState | TaskState | DecisionState | HandoffState | TerminalState;

export type SkillFlowTransition = {
  id: string;
  fromStateId: string;
  toStateId: string;
  label: string;
  kind: SkillFlowTransitionKind;
  priority: number;
  predicate?: BranchPredicate;
};

export type SkillFlowDocument = {
  version: '3';
  metadata: SkillFlowMetadata;
  entryStateId: string;
  states: Record<string, SkillFlowState>;
  transitions: Record<string, SkillFlowTransition>;
};

export type SkillFlowValidationResult = {
  isValid: boolean;
  errors: string[];
  warnings: string[];
};

export type CompiledSkillFlow = {
  document: SkillFlowDocument;
  entryStateId: string;
  outgoingByStateId: Record<string, SkillFlowTransition[]>;
  incomingByStateId: Record<string, SkillFlowTransition[]>;
  terminalStateIds: string[];
  orderedBranchesByDecisionStateId: Record<string, SkillFlowTransition[]>;
  validation: SkillFlowValidationResult;
};

export type SkillWorkbenchTool = {
  id: string;
  name: string;
  description: string | null;
  isEnabled: boolean;
  isRequired: boolean;
  config: Record<string, unknown>;
};
