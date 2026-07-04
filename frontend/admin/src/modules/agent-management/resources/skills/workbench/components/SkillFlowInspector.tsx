import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, LifeBuoy, Trash2, UserRoundPlus } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { NumberField, SelectField, TextAreaField, TextField } from '@/shared/ui/FormFields';
import type {
  InputField,
  OutputField,
  SkillFlowDocument,
  SkillFlowState,
  SkillFlowTransition,
  SkillWorkbenchTool,
  TaskState,
} from '../lib/types';
import type { TaskBranchDraft } from '../state/useSkillFlowBuilderStore';

function getSelectedState(
  document: SkillFlowDocument,
  selection: { kind: 'state' | 'transition'; id: string } | null,
): SkillFlowState | null {
  if (!selection || selection.kind !== 'state') {
    return null;
  }

  return document.states[selection.id] ?? null;
}

function getSelectedTransition(
  document: SkillFlowDocument,
  selection: { kind: 'state' | 'transition'; id: string } | null,
): SkillFlowTransition | null {
  if (!selection || selection.kind !== 'transition') {
    return null;
  }

  return document.transitions[selection.id] ?? null;
}

type InspectorProps = {
  document: SkillFlowDocument;
  selection: { kind: 'state' | 'transition'; id: string } | null;
  toolLibrary: SkillWorkbenchTool[];
  validation: { isValid: boolean; errors: string[]; warnings: string[] };
  onAddBranch?: (stateId: string, targetKind: 'terminal' | 'handoff') => void;
  onAddTaskBranch?: (stateId: string, draft: TaskBranchDraft) => void;
  onAddTool: (stateId: string, toolId: string) => void;
  onDeleteState?: (stateId: string) => void;
  onRemoveTool: (stateId: string, toolId: string) => void;
  onUpdateDecisionState?: (
    stateId: string,
    patch: { title?: string; question?: string },
  ) => void;
  onUpdateHandoffState?: (
    stateId: string,
    patch: { title?: string; handoffType?: 'human' | 'ticket' | 'other_agent'; summaryTemplate?: string },
  ) => void;
  onUpdateTaskState: (
    stateId: string,
    patch: Partial<Pick<TaskState, 'title' | 'goal' | 'inputContract' | 'outputContract' | 'fallbackPolicy'>>,
  ) => void;
  onUpdateTerminalState?: (
    stateId: string,
    patch: { title?: string; outcome?: 'resolved' | 'blocked' | 'cancelled'; resolutionNote?: string },
  ) => void;
  onUpdateToolPlanReason?: (stateId: string, toolId: string, reason: string) => void;
  onUpdateTransition?: (
    transitionId: string,
    patch: Partial<Pick<SkillFlowTransition, 'label' | 'kind' | 'priority' | 'predicate'>>,
  ) => void;
};


function serializeFields(fields: Array<InputField | OutputField>) {
  return fields.map((field) => field.label).join('\n');
}

function slugifyFieldKey(label: string) {
  return label
    .trim()
    .toLowerCase()
    .replace(/[\s/]+/g, '_')
    .replace(/[^\p{L}\p{N}_-]+/gu, '')
    .replace(/^_+|_+$/g, '');
}

function parseFields(value: string, existingFields: Array<InputField | OutputField> = []) {
  const existingFieldsByLabel = new Map(existingFields.map((field) => [field.label, field.key]));

  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
    .map((label) => ({
      key: existingFieldsByLabel.get(label) ?? slugifyFieldKey(label),
      label,
    }));
}

function getTaskBranchTone(kind: SkillFlowTransition['kind']) {
  if (kind === 'fallback') {
    return 'warning';
  }

  if (kind === 'error') {
    return 'danger';
  }

  return 'neutral';
}


export function SkillFlowInspector(props: InspectorProps) {
  const { t } = useTranslation('common');
  const wb = 'modules.agentManagement.skills.workbench';
  const wbi = `${wb}.inspector`;
  const selectedState = getSelectedState(props.document, props.selection);
  const selectedTransition = getSelectedTransition(props.document, props.selection);

  if (selectedTransition) {
    return (
      <TransitionInspector
        transition={selectedTransition}
        onUpdateTransition={props.onUpdateTransition}
      />
    );
  }

  if (!selectedState) {
    return (
      <EmptyState
        title={t(`${wbi}.noSelectionTitle`)}
        description={props.validation.isValid ? t(`${wbi}.noSelectionDescription`) : props.validation.errors[0]}
      />
    );
  }

  switch (selectedState.kind) {
    case 'task':
      return (
        <TaskStateInspector
          document={props.document}
          state={selectedState}
          toolLibrary={props.toolLibrary}
          onAddTaskBranch={props.onAddTaskBranch}
          onAddTool={props.onAddTool}
          onDeleteState={props.onDeleteState}
          onRemoveTool={props.onRemoveTool}
          onUpdateTaskState={props.onUpdateTaskState}
          onUpdateToolPlanReason={props.onUpdateToolPlanReason}
        />
      );
    case 'decision':
      return (
        <DecisionStateInspector
          state={selectedState}
          document={props.document}
          onAddBranch={props.onAddBranch}
          onUpdateDecisionState={props.onUpdateDecisionState}
        />
      );
    case 'handoff':
      return (
        <HandoffStateInspector
          state={selectedState}
          onDeleteState={props.onDeleteState}
          onUpdateHandoffState={props.onUpdateHandoffState}
        />
      );
    case 'terminal':
      return (
        <TerminalStateInspector
          state={selectedState}
          onDeleteState={props.onDeleteState}
          onUpdateTerminalState={props.onUpdateTerminalState}
        />
      );
    default:
      return (
        <EmptyState
          title={t(`${wbi}.startNodeTitle`)}
          description={t(`${wbi}.startNodeDescription`)}
        />
      );
  }
}

function DecisionStateInspector(props: {
  state: Extract<SkillFlowState, { kind: 'decision' }>;
  document: SkillFlowDocument;
  onAddBranch?: (stateId: string, targetKind: 'terminal' | 'handoff') => void;
  onUpdateDecisionState?: (stateId: string, patch: { title?: string; question?: string }) => void;
}) {
  const { t } = useTranslation('common');
  const wbi = 'modules.agentManagement.skills.workbench.inspector';
  const outgoingTransitions = Object.values(props.document.transitions).filter(
    (transition) => transition.fromStateId === props.state.id,
  );

  return (
    <div className="space-y-4">
      <TextField
        label={t(`${wbi}.decisionTitle`)}
        value={props.state.title}
        onChange={(event) => props.onUpdateDecisionState?.(props.state.id, { title: event.target.value })}
      />
      <TextAreaField
        label={t(`${wbi}.decisionQuestion`)}
        value={props.state.question}
        rows={4}
        onChange={(event) => props.onUpdateDecisionState?.(props.state.id, { question: event.target.value })}
      />

      <section className="rounded-[2px] border border-border bg-background-subtle p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-text">{t(`${wbi}.decisionBranchSectionTitle`)}</div>
            <div className="mt-1 text-sm text-text-secondary">{t(`${wbi}.decisionBranchSectionDescription`)}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => props.onAddBranch?.(props.state.id, 'terminal')}>
              {t(`${wbi}.addConditionBranch`)}
            </Button>
            <Button variant="secondary" onClick={() => props.onAddBranch?.(props.state.id, 'handoff')}>
              {t(`${wbi}.addDecisionHandoffBranch`)}
            </Button>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          {outgoingTransitions.map((transition) => (
            <div key={transition.id} className="rounded-[2px] border border-border bg-surface px-3 py-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium text-text">{transition.label || transition.id}</div>
                  <div className="mt-1 text-xs text-text-muted">
                    {t(`${wbi}.transitionKindPriority`, { kind: transition.kind, priority: transition.priority })}
                  </div>
                </div>
                <Badge tone={transition.kind === 'handoff' ? 'warning' : 'neutral'}>
                  {transition.kind === 'handoff' ? t(`${wbi}.transitionKindHandoff`) : t(`${wbi}.transitionKindCondition`)}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function HandoffStateInspector(props: {
  state: Extract<SkillFlowState, { kind: 'handoff' }>;
  onDeleteState?: (stateId: string) => void;
  onUpdateHandoffState?: (
    stateId: string,
    patch: { title?: string; handoffType?: 'human' | 'ticket' | 'other_agent'; summaryTemplate?: string },
  ) => void;
}) {
  const { t } = useTranslation('common');
  const wbi = 'modules.agentManagement.skills.workbench.inspector';
  return (
    <div className="space-y-4">
      <InspectorDeleteButton label={t(`${wbi}.deleteHandoff`)} onDelete={props.onDeleteState} stateId={props.state.id} />

      <TextField
        label={t(`${wbi}.handoffTitle`)}
        value={props.state.title}
        onChange={(event) => props.onUpdateHandoffState?.(props.state.id, { title: event.target.value })}
      />
      <SelectField
        label={t(`${wbi}.handoffTypeLabel`)}
        value={props.state.handoffType}
        onChange={(event) =>
          props.onUpdateHandoffState?.(props.state.id, {
            handoffType: event.target.value as 'human' | 'ticket' | 'other_agent',
          })
        }
      >
        <option value="human">{t(`${wbi}.handoffTypeHuman`)}</option>
        <option value="ticket">{t(`${wbi}.handoffTypeTicket`)}</option>
        <option value="other_agent">{t(`${wbi}.handoffTypeOtherAgent`)}</option>
      </SelectField>
      <TextAreaField
        label={t(`${wbi}.handoffSummaryLabel`)}
        value={props.state.summaryTemplate}
        rows={6}
        onChange={(event) =>
          props.onUpdateHandoffState?.(props.state.id, { summaryTemplate: event.target.value })
        }
      />
    </div>
  );
}

function TerminalStateInspector(props: {
  state: Extract<SkillFlowState, { kind: 'terminal' }>;
  onDeleteState?: (stateId: string) => void;
  onUpdateTerminalState?: (
    stateId: string,
    patch: { title?: string; outcome?: 'resolved' | 'blocked' | 'cancelled'; resolutionNote?: string },
  ) => void;
}) {
  const { t } = useTranslation('common');
  const wbi = 'modules.agentManagement.skills.workbench.inspector';
  return (
    <div className="space-y-4">
      <InspectorDeleteButton label={t(`${wbi}.deleteTerminal`)} onDelete={props.onDeleteState} stateId={props.state.id} />

      <TextField
        label={t(`${wbi}.terminalTitle`)}
        value={props.state.title}
        onChange={(event) => props.onUpdateTerminalState?.(props.state.id, { title: event.target.value })}
      />
      <SelectField
        label={t(`${wbi}.terminalOutcomeLabel`)}
        value={props.state.outcome}
        onChange={(event) =>
          props.onUpdateTerminalState?.(props.state.id, {
            outcome: event.target.value as 'resolved' | 'blocked' | 'cancelled',
          })
        }
      >
        <option value="resolved">{t(`${wbi}.terminalResolved`)}</option>
        <option value="blocked">{t(`${wbi}.terminalBlocked`)}</option>
        <option value="cancelled">{t(`${wbi}.terminalCancelled`)}</option>
      </SelectField>
      <TextAreaField
        label={t(`${wbi}.terminalNoteLabel`)}
        value={props.state.resolutionNote}
        rows={5}
        onChange={(event) =>
          props.onUpdateTerminalState?.(props.state.id, { resolutionNote: event.target.value })
        }
      />
    </div>
  );
}

function TransitionInspector(props: {
  transition: SkillFlowTransition;
  onUpdateTransition?: (
    transitionId: string,
    patch: Partial<Pick<SkillFlowTransition, 'label' | 'kind' | 'priority' | 'predicate'>>,
  ) => void;
}) {
  const { t } = useTranslation('common');
  const wb = 'modules.agentManagement.skills.workbench';
  const wbi = `${wb}.inspector`;
  const transitionKindOptions = [
    { value: 'default', label: t(`${wb}.edgeTypes.default`) },
    { value: 'condition', label: t(`${wb}.edgeTypes.condition`) },
    { value: 'fallback', label: t(`${wb}.edgeTypes.fallback`) },
    { value: 'error', label: t(`${wb}.edgeTypes.error`) },
    { value: 'handoff', label: t(`${wb}.edgeTypes.handoff`) },
  ];
  const predicateValue = props.transition.predicate
    ? props.transition.predicate.expression.operator === 'in'
      ? props.transition.predicate.expression.value.join(', ')
      : props.transition.predicate.expression.value
    : '';

  return (
    <div className="space-y-4">
      <TextField
        label={t(`${wbi}.transitionName`)}
        value={props.transition.label}
        onChange={(event) => props.onUpdateTransition?.(props.transition.id, { label: event.target.value })}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <SelectField
          label={t(`${wbi}.transitionType`)}
          value={props.transition.kind}
          onChange={(event) =>
            props.onUpdateTransition?.(props.transition.id, {
              kind: event.target.value as SkillFlowTransition['kind'],
            })
          }
        >
          {transitionKindOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectField>
        <NumberField
          label={t(`${wbi}.transitionPriorityLabel`)}
          value={props.transition.priority}
          onChange={(event) =>
            props.onUpdateTransition?.(props.transition.id, {
              priority: Number(event.target.value || 0),
            })
          }
        />
      </div>

      <TextAreaField
        label={t(`${wbi}.transitionCondition`)}
        value={props.transition.predicate?.description ?? ''}
        rows={3}
        onChange={(event) =>
          props.onUpdateTransition?.(props.transition.id, {
            predicate: {
              description: event.target.value,
              expression: props.transition.predicate?.expression ?? {
                field: 'route',
                operator: 'eq',
                value: '',
              },
            },
          })
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <TextField
          label={t(`${wbi}.transitionField`)}
          value={props.transition.predicate?.expression.field ?? 'route'}
          onChange={(event) =>
            props.onUpdateTransition?.(props.transition.id, {
              predicate: {
                description: props.transition.predicate?.description ?? '',
                expression: {
                  ...(props.transition.predicate?.expression ?? { operator: 'eq', value: '' }),
                  field: event.target.value,
                },
              },
            })
          }
        />
        <SelectField
          label={t(`${wbi}.transitionOperator`)}
          value={props.transition.predicate?.expression.operator ?? 'eq'}
          onChange={(event) => {
            const operator = event.target.value as 'eq' | 'in';
            props.onUpdateTransition?.(props.transition.id, {
              predicate: {
                description: props.transition.predicate?.description ?? '',
                expression: operator === 'in'
                  ? {
                      field: props.transition.predicate?.expression.field ?? 'route',
                      operator,
                      value: predicateValue
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }
                  : {
                      field: props.transition.predicate?.expression.field ?? 'route',
                      operator,
                      value: predicateValue,
                    },
              },
            });
          }}
        >
          <option value="eq">{t(`${wbi}.operatorEq`)}</option>
          <option value="in">{t(`${wbi}.operatorIn`)}</option>
        </SelectField>
        <TextField
          label={t(`${wbi}.transitionValue`)}
          value={predicateValue}
          onChange={(event) => {
            const expression = props.transition.predicate?.expression;
            props.onUpdateTransition?.(props.transition.id, {
              predicate: {
                description: props.transition.predicate?.description ?? '',
                expression: expression?.operator === 'in'
                  ? {
                      field: expression.field,
                      operator: 'in',
                      value: event.target.value
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }
                  : {
                      field: expression?.field ?? 'route',
                      operator: 'eq',
                      value: event.target.value,
                    },
              },
            });
          }}
        />
      </div>
    </div>
  );
}

function TaskStateInspector(props: {
  document: SkillFlowDocument;
  state: TaskState;
  toolLibrary: SkillWorkbenchTool[];
  onAddTaskBranch?: (stateId: string, draft: TaskBranchDraft) => void;
  onAddTool: (stateId: string, toolId: string) => void;
  onDeleteState?: (stateId: string) => void;
  onRemoveTool: (stateId: string, toolId: string) => void;
  onUpdateTaskState: (
    stateId: string,
    patch: Partial<Pick<TaskState, 'title' | 'goal' | 'inputContract' | 'outputContract' | 'fallbackPolicy'>>,
  ) => void;
  onUpdateToolPlanReason?: (stateId: string, toolId: string, reason: string) => void;
}) {
  const { t } = useTranslation('common');
  const wb = 'modules.agentManagement.skills.workbench';
  const wbi = `${wb}.inspector`;
  const [toolPickerOpen, setToolPickerOpen] = useState(false);
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const selectedTools = props.state.toolPlan.map((plan) => ({
    plan,
    tool: props.toolLibrary.find((candidate) => candidate.id === plan.toolId) ?? null,
  }));
  const availableTools = props.toolLibrary.filter(
    (tool) => !props.state.toolPlan.some((plan) => plan.toolId === tool.id),
  );
  const inspectedToolId = props.state.toolPlan.some((plan) => plan.toolId === selectedToolId)
    ? selectedToolId
    : props.state.toolPlan[0]?.toolId ?? null;
  const inspectedPlan = props.state.toolPlan.find((plan) => plan.toolId === inspectedToolId) ?? null;
  const inspectedTool = inspectedPlan
    ? props.toolLibrary.find((candidate) => candidate.id === inspectedPlan.toolId) ?? null
    : null;
  const outgoingTransitions = Object.values(props.document.transitions)
    .filter((transition) => transition.fromStateId === props.state.id)
    .sort((left, right) => left.priority - right.priority);
  const fallbackTransitions = outgoingTransitions.filter((transition) => transition.kind === 'fallback');
  const nonDefaultBranches = outgoingTransitions.filter((transition) => transition.kind !== 'default');

  useEffect(() => {
    setToolPickerOpen(false);
    setSelectedToolId(null);
  }, [props.state.id]);

  function updateFallbackMode(nextMode: TaskState['fallbackPolicy']['mode']) {
    if (nextMode === 'stay') {
      props.onUpdateTaskState(props.state.id, {
        fallbackPolicy: { mode: 'stay', note: props.state.fallbackPolicy.note },
      });
      return;
    }

    if (nextMode === 'handoff') {
      props.onUpdateTaskState(props.state.id, {
        fallbackPolicy: { mode: 'handoff', note: props.state.fallbackPolicy.note },
      });
      return;
    }

    props.onUpdateTaskState(props.state.id, {
      fallbackPolicy: {
        mode: 'goto',
        transitionId: fallbackTransitions[0]?.id ?? '',
        note: props.state.fallbackPolicy.note,
      },
    });
  }

  return (
    <div className="space-y-4">
      <InspectorDeleteButton label={t(`${wbi}.deleteTask`)} onDelete={props.onDeleteState} stateId={props.state.id} />

      <TextField
        label={t(`${wbi}.taskTitle`)}
        value={props.state.title}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, { title: event.target.value });
        }}
      />

      <TextAreaField
        label={t(`${wbi}.taskGoal`)}
        value={props.state.goal}
        rows={5}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, { goal: event.target.value });
        }}
      />

      <TextAreaField
        label={t(`${wbi}.taskInherited`)}
        value={serializeFields(props.state.inputContract.inherited)}
        rows={3}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, {
            inputContract: {
              inherited: parseFields(event.target.value, props.state.inputContract.inherited),
              required: props.state.inputContract.required.map((field) => ({ ...field })),
              optional: props.state.inputContract.optional.map((field) => ({ ...field })),
            },
          });
        }}
      />

      <TextAreaField
        label={t(`${wbi}.taskRequired`)}
        value={serializeFields(props.state.inputContract.required)}
        rows={4}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, {
            inputContract: {
              inherited: props.state.inputContract.inherited.map((field) => ({ ...field })),
              required: parseFields(event.target.value, props.state.inputContract.required),
              optional: props.state.inputContract.optional.map((field) => ({ ...field })),
            },
          });
        }}
      />

      <TextAreaField
        label={t(`${wbi}.taskOptional`)}
        value={serializeFields(props.state.inputContract.optional)}
        rows={3}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, {
            inputContract: {
              inherited: props.state.inputContract.inherited.map((field) => ({ ...field })),
              required: props.state.inputContract.required.map((field) => ({ ...field })),
              optional: parseFields(event.target.value, props.state.inputContract.optional),
            },
          });
        }}
      />

      <TextAreaField
        label={t(`${wbi}.taskOutput`)}
        value={serializeFields(props.state.outputContract)}
        rows={4}
        onChange={(event) => {
          props.onUpdateTaskState(props.state.id, {
            outputContract: parseFields(event.target.value, props.state.outputContract),
          });
        }}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <SelectField
          label={t(`${wbi}.fallbackPolicyLabel`)}
          value={props.state.fallbackPolicy.mode}
          onChange={(event) => updateFallbackMode(event.target.value as TaskState['fallbackPolicy']['mode'])}
        >
          <option value="stay">{t(`${wbi}.fallbackStay`)}</option>
          <option value="handoff">{t(`${wbi}.fallbackHandoffOption`)}</option>
          <option value="goto">{t(`${wbi}.fallbackGoto`)}</option>
        </SelectField>

        {props.state.fallbackPolicy.mode === 'goto' ? (
          <SelectField
            label={t(`${wbi}.fallbackTargetLabel`)}
            value={props.state.fallbackPolicy.transitionId}
            onChange={(event) => {
              props.onUpdateTaskState(props.state.id, {
                fallbackPolicy: {
                  mode: 'goto',
                  transitionId: event.target.value,
                  note: props.state.fallbackPolicy.note,
                },
              });
            }}
          >
            <option value="">{t(`${wbi}.fallbackTargetPlaceholder`)}</option>
            {fallbackTransitions.map((transition) => (
              <option key={transition.id} value={transition.id}>
                {transition.label}
              </option>
            ))}
          </SelectField>
        ) : (
          <TextField label={t(`${wbi}.fallbackTargetLabel`)} value={t(`${wbi}.fallbackTargetDisabled`)} disabled />
        )}
      </div>

      <TextAreaField
        label={t(`${wbi}.fallbackNoteLabel`)}
        value={props.state.fallbackPolicy.note}
        rows={4}
        onChange={(event) => {
          if (props.state.fallbackPolicy.mode === 'goto') {
            props.onUpdateTaskState(props.state.id, {
              fallbackPolicy: {
                ...props.state.fallbackPolicy,
                note: event.target.value,
              },
            });
            return;
          }

          props.onUpdateTaskState(props.state.id, {
            fallbackPolicy: {
              mode: props.state.fallbackPolicy.mode,
              note: event.target.value,
            },
          });
        }}
      />

      <section className="rounded-[2px] border border-border bg-background-subtle p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-text">{t(`${wbi}.branchSectionTitle`)}</div>
            <div className="mt-1 text-sm text-text-secondary">{t(`${wbi}.branchSectionDescription`)}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => props.onAddTaskBranch?.(props.state.id, { transitionKind: 'fallback', targetKind: 'handoff' })}
            >
              <LifeBuoy size={16} />
              {t(`${wbi}.addFallbackBranch`)}
            </Button>
            <Button
              variant="secondary"
              onClick={() => props.onAddTaskBranch?.(props.state.id, { transitionKind: 'error', targetKind: 'terminal' })}
            >
              <AlertTriangle size={16} />
              {t(`${wbi}.addErrorBranch`)}
            </Button>
            <Button
              variant="secondary"
              onClick={() => props.onAddTaskBranch?.(props.state.id, { transitionKind: 'handoff', targetKind: 'handoff' })}
            >
              <UserRoundPlus size={16} />
              {t(`${wbi}.addHandoffBranch`)}
            </Button>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          {nonDefaultBranches.length === 0 ? (
            <div className="rounded-[2px] border border-dashed border-border bg-surface px-3 py-2 text-sm text-text-secondary">
              {t(`${wbi}.noBranches`)}
            </div>
          ) : (
            nonDefaultBranches.map((transition) => {
              const targetState = props.document.states[transition.toStateId];
              return (
                <div key={transition.id} className="rounded-[2px] border border-border bg-surface px-3 py-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-medium text-text">{transition.label || transition.id}</div>
                      <div className="mt-1 text-sm text-text-secondary">
                        {t(`${wbi}.targetNode`, { title: targetState?.title ?? transition.toStateId })}
                      </div>
                    </div>
                    <Badge tone={getTaskBranchTone(transition.kind)}>
                      {transition.kind === 'fallback'
                        ? t(`${wbi}.branchLabelFallback`)
                        : transition.kind === 'error'
                          ? t(`${wbi}.branchLabelError`)
                          : t(`${wbi}.branchLabelHandoff`)}</Badge>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      <section className="rounded-[2px] border border-border bg-background-subtle p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-text">{t(`${wbi}.toolSectionTitle`)}</div>
            <div className="mt-1 text-sm text-text-secondary">{t(`${wbi}.toolSectionDescription`)}</div>
          </div>
          <Button
            variant="secondary"
            onClick={() => {
              setToolPickerOpen((open) => !open);
            }}
          >
            {t(`${wbi}.addToolButton`)}
          </Button>
        </div>

        <div className="mt-3 space-y-3">
          {selectedTools.length === 0 ? (
            <div className="rounded-[2px] border border-dashed border-border bg-surface px-3 py-2 text-sm text-text-secondary">
              {t(`${wbi}.noTools`)}
            </div>
          ) : (
            selectedTools.map(({ plan, tool }) => {
              const isActive = inspectedPlan?.toolId === plan.toolId;

              return (
                <div
                  key={plan.id}
                  className={`rounded-[2px] border px-3 py-3 text-sm ${isActive ? 'border-primary/25 bg-surface' : 'border-border bg-surface'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <button
                        type="button"
                        className="min-w-0 truncate text-left font-medium text-text"
                        onClick={() => setSelectedToolId(plan.toolId)}
                      >
                        {tool?.name ?? plan.toolId}
                      </button>
                      <div className="mt-1 text-sm text-text-secondary">{plan.reason}</div>
                    </div>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        props.onRemoveTool(props.state.id, plan.toolId);
                      }}
                    >
                      {t(`${wbi}.removeTool`)}
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {toolPickerOpen ? (
          <div className="mt-3 space-y-3 rounded-[2px] border border-border bg-surface p-3">
            {availableTools.length === 0 ? (
              <div className="text-sm text-text-secondary">{t(`${wbi}.noAvailableTools`)}</div>
            ) : (
              availableTools.map((tool) => (
                <div key={tool.id} className="flex flex-col gap-3 rounded-[2px] border border-border bg-background-subtle p-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-semibold text-text">{tool.name}</span>
                      {tool.isRequired ? <Badge tone="warning">{t(`${wbi}.requiredBadge`)}</Badge> : null}
                    </div>
                    <div className="mt-1 text-sm text-text-secondary">{tool.description ?? t(`${wbi}.noDescription`)}</div>
                  </div>
                  <div className="flex justify-end">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        props.onAddTool(props.state.id, tool.id);
                        setSelectedToolId(tool.id);
                        setToolPickerOpen(false);
                      }}
                    >
                      {t(`${wbi}.addToolById`, { id: tool.id })}
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : null}

        {inspectedPlan ? (
          <div className="mt-3 rounded-[2px] border border-border bg-surface p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-text">{t(`${wbi}.toolDetailTitle`, { name: inspectedTool?.name ?? inspectedPlan.toolId })}</div>
                <div className="mt-1 text-sm text-text-secondary">
                  {inspectedTool?.description ?? t(`${wbi}.toolNotFound`)}
                </div>
              </div>
              {inspectedTool?.isRequired ? <Badge tone="warning">{t(`${wbi}.requiredBadge`)}</Badge> : null}
            </div>

            <div className="mt-3">
              <TextAreaField
                label={t(`${wbi}.toolCallReason`)}
                value={inspectedPlan.reason}
                rows={4}
                onChange={(event) =>
                  props.onUpdateToolPlanReason?.(props.state.id, inspectedPlan.toolId, event.target.value)
                }
              />
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function InspectorDeleteButton(props: {
  label: string;
  stateId: string;
  onDelete?: (stateId: string) => void;
}) {
  if (!props.onDelete) {
    return null;
  }

  return (
    <div className="flex justify-end">
      <Button variant="ghost" onClick={() => props.onDelete?.(props.stateId)}>
        <Trash2 size={16} />
        {props.label}
      </Button>
    </div>
  );
}
