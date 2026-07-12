import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Save, Shuffle } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { PageFrame } from '@/shared/ui/PageFrame';
import { Skeleton } from '@/shared/ui/Skeleton';
import { useSkill, useSkillMutations } from './hooks';
import type { SkillDetailView } from './types';
import { toSkillDefinitionApiUpdateRequest } from './types';
import { SkillFlowCanvas } from './workbench/components/SkillFlowCanvas';
import { SkillFlowInspector } from './workbench/components/SkillFlowInspector';
import { SkillFlowOutline } from './workbench/components/SkillFlowOutline';
import { SkillFlowValidationPanel } from './workbench/components/SkillFlowValidationPanel';
import {
  buildWorkbenchToolLibrary,
  createDefaultSkillFlowDocument,
  syncSkillFlowMetadata,
} from './workbench/lib/documents';
import type { SkillFlowDocument } from './workbench/lib/types';
import {
  SkillFlowBuilderStoreProvider,
  useSkillFlowBuilderActions,
  useSkillFlowBuilderState,
  type TaskBranchDraft,
} from './workbench/state/useSkillFlowBuilderStore';

const am = 'agentManagement:';

function serializeRemoteSkill({
  skillKey,
  displayName,
  description,
  version,
  toolBindings,
  orchestration,
}: Pick<SkillDetailView, 'skillKey' | 'displayName' | 'description' | 'version' | 'toolBindings' | 'orchestration'>) {
  return JSON.stringify({
    skillKey,
    displayName,
    description,
    version,
    toolBindings,
    orchestration,
  });
}

type PendingRemoteUpdate = {
  skill: SkillDetailView;
  document: SkillFlowDocument;
  signature: string;
};

function SkillWorkbenchPageContent({ skillKey }: { skillKey: string }) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const navigate = useNavigate();
  const skillQuery = useSkill(skillKey);
  const mutations = useSkillMutations();
  const [showFlowCanvas, setShowFlowCanvas] = useState(false);
  const [showValidation, setShowValidation] = useState(false);

  const {
    document,
    compiled,
    nodes,
    edges,
    selection,
    dirty,
    error,
  } = useSkillFlowBuilderState();
  const {
    load,
    reset,
    setSelection,
    onNodesChange,
    onEdgesChange,
    addTaskStateBeforeState,
    addTaskStateAfterState,
    addDecisionAfterState,
    addBranchToDecisionState,
    updateTaskState,
    updateDecisionState,
    updateHandoffState,
    updateTerminalState,
    updateTransition,
    addTaskBranch,
    deleteState,
    addToolToTaskState,
    removeToolFromTaskState,
    updateToolPlanReason,
    applyLayout,
  } = useSkillFlowBuilderActions();

  const remoteBaselineSignatureRef = useRef<string | null>(null);
  const [loadedSkill, setLoadedSkill] = useState<SkillDetailView | null>(null);
  const [pendingRemoteUpdate, setPendingRemoteUpdate] = useState<PendingRemoteUpdate | null>(null);

  const wb = `${am}skills.workbench`;
  const defaults = `${wb}.defaults`;

  const handleAddTaskStateAfterState = useCallback((stateId: string) => {
    addTaskStateAfterState(stateId, t(`${defaults}.taskTitle`));
  }, [addTaskStateAfterState, t, defaults]);

  const handleAddTaskStateBeforeState = useCallback((stateId: string) => {
    addTaskStateBeforeState(stateId, t(`${defaults}.taskTitle`));
  }, [addTaskStateBeforeState, t, defaults]);

  const handleAddDecisionAfterState = useCallback((stateId: string) => {
    addDecisionAfterState(stateId, {
      decisionTitle: t(`${defaults}.decisionTitle`),
      decisionQuestion: t(`${defaults}.decisionQuestion`),
      enterLabel: t(`${defaults}.enterDecisionLabel`),
      continueLabel: t(`${defaults}.continueAutoLabel`),
      continueDescription: t(`${defaults}.continueAutoDescription`),
      handoffBranchLabel: t(`${defaults}.handoffBranchLabel`),
      handoffTitle: t(`${defaults}.handoffTitle`),
      handoffSummary: t(`${defaults}.handoffSummary`),
    });
  }, [addDecisionAfterState, t, defaults]);

  const handleAddBranchToDecisionState = useCallback((stateId: string, targetKind: 'terminal' | 'handoff') => {
    addBranchToDecisionState(stateId, targetKind, {
      handoffLabel: t(`${defaults}.branchHandoffLabel`),
      terminalLabel: t(`${defaults}.branchTerminalLabel`),
      conditionDescription: (n: number) => t(`${defaults}.branchConditionDescription`, { n }),
      handoffTitle: t(`${defaults}.handoffTitle`),
      handoffSummary: t(`${defaults}.handoffSummary`),
      terminalTitle: t(`${defaults}.terminalTitle`),
      terminalNote: t(`${defaults}.terminalNote`),
    });
  }, [addBranchToDecisionState, t, defaults]);

  const handleAddTaskBranch = useCallback((stateId: string, draft: TaskBranchDraft) => {
    let transitionLabel: string;
    if (draft.transitionKind === 'handoff') {
      transitionLabel = t(`${defaults}.taskBranchHandoff`);
    } else if (draft.transitionKind === 'fallback') {
      transitionLabel = draft.targetKind === 'handoff'
        ? t(`${defaults}.taskBranchFallbackHandoff`)
        : t(`${defaults}.taskBranchFallbackTerminal`);
    } else {
      transitionLabel = draft.targetKind === 'handoff'
        ? t(`${defaults}.taskBranchErrorHandoff`)
        : t(`${defaults}.taskBranchErrorTerminal`);
    }
    addTaskBranch(stateId, draft, {
      transitionLabel,
      fallbackNote: t(`${defaults}.fallbackNote`),
      handoffTitle: t(`${defaults}.handoffTitle`),
      handoffSummary: t(`${defaults}.handoffSummary`),
      terminalTitle: t(`${defaults}.terminalTitle`),
      terminalNote: t(`${defaults}.terminalNote`),
    });
  }, [addTaskBranch, t, defaults]);

  useEffect(() => {
    setShowFlowCanvas(false);
    setShowValidation(false);
  }, [skillKey]);

  useEffect(() => {
    if (!skillQuery.data) {
      if (!skillQuery.isLoading) {
        reset();
        setLoadedSkill(null);
        remoteBaselineSignatureRef.current = null;
        setPendingRemoteUpdate(null);
      }
      return;
    }

    const nextRemoteDocument = syncSkillFlowMetadata(
      skillQuery.data.orchestration ?? createDefaultSkillFlowDocument(skillQuery.data),
      skillQuery.data,
    );
    const nextSignature = serializeRemoteSkill({
      skillKey: skillQuery.data.skillKey,
      displayName: skillQuery.data.displayName,
      description: skillQuery.data.description,
      version: skillQuery.data.version,
      toolBindings: skillQuery.data.toolBindings,
      orchestration: nextRemoteDocument,
    });

    if (remoteBaselineSignatureRef.current === null) {
      load(nextRemoteDocument);
      setLoadedSkill(skillQuery.data);
      remoteBaselineSignatureRef.current = nextSignature;
      setPendingRemoteUpdate(null);
      return;
    }

    if (remoteBaselineSignatureRef.current === nextSignature) {
      return;
    }

    if (dirty && document?.metadata.skillKey === skillQuery.data.skillKey) {
      setPendingRemoteUpdate((current) =>
        current?.signature === nextSignature
          ? current
          : {
              skill: skillQuery.data,
              document: nextRemoteDocument,
              signature: nextSignature,
            },
      );
      return;
    }

    load(nextRemoteDocument);
    setLoadedSkill(skillQuery.data);
    remoteBaselineSignatureRef.current = nextSignature;
    setPendingRemoteUpdate(null);
  }, [document?.metadata.skillKey, dirty, load, reset, skillQuery.data, skillQuery.isLoading]);

  const toolBindings = loadedSkill?.toolBindings ?? skillQuery.data?.toolBindings ?? [];
  const toolLibrary = buildWorkbenchToolLibrary(toolBindings);

  if (skillQuery.isLoading) {
    return (
      <PageFrame title={t(`${am}skills.workbench.title`)}>
        <div className="space-y-4">
          <InlineMessage tone="info">{t(`${am}skills.workbench.loadingMessage`)}</InlineMessage>
          <Skeleton className="h-64" />
        </div>
      </PageFrame>
    );
  }

  if (skillQuery.isError || !skillQuery.data) {
    return (
      <PageFrame title={t(`${am}skills.workbench.title`)}>
        <InlineMessage tone="error">
          {mutations.getMutationMessage(skillQuery.error ?? new Error(t(`${am}skills.workbench.skillNotFound`)))}
        </InlineMessage>
      </PageFrame>
    );
  }
  const skill = loadedSkill ?? skillQuery.data;
  const auxPanelCount = Number(showFlowCanvas) + Number(showValidation);

  async function handleSave() {
    if (!document) {
      return;
    }

    const nextDocument = syncSkillFlowMetadata(document, skill);
    await mutations.update.mutateAsync({
      skillKey: skill.skillKey,
      model: toSkillDefinitionApiUpdateRequest({
        displayName: skill.displayName,
        description: skill.description,
        version: skill.version,
        tags: skill.tags,
        promptSections: skill.promptSections,
        toolBindings: skill.toolBindings,
        configSchema: skill.configSchema,
        spec: skill.spec,
        orchestration: nextDocument,
      }),
    });

    load(nextDocument);
    setLoadedSkill(skill);
    remoteBaselineSignatureRef.current = serializeRemoteSkill({
      skillKey: skill.skillKey,
      displayName: skill.displayName,
      description: skill.description,
      version: skill.version,
      toolBindings: skill.toolBindings,
      orchestration: nextDocument,
    });
    setPendingRemoteUpdate(null);
  }

  function handleApplyRemoteVersion() {
    if (!pendingRemoteUpdate) {
      return;
    }

    load(pendingRemoteUpdate.document);
    setLoadedSkill(pendingRemoteUpdate.skill);
    remoteBaselineSignatureRef.current = pendingRemoteUpdate.signature;
    setPendingRemoteUpdate(null);
  }

  return (
    <PageFrame
      eyebrow={t(`${am}skills.workbench.eyebrow`)}
      title={t(`${am}skills.workbench.pageTitle`, { name: skill.displayName })}
      contentClassName="min-h-0 flex flex-col"
      scroll={false}
      actions={(
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => navigate('/agent-management/skills')}
            data-testid="skill-workbench-back"
          >
            <ArrowLeft size={16} />
            {t(`${am}skills.workbench.backToList`)}
          </Button>
          <Button
            variant="secondary"
            onClick={() => applyLayout('TB')}
            disabled={!document}
            data-testid="skill-workbench-auto-layout"
          >
            <Shuffle size={16} />
            {t(`${am}skills.workbench.autoLayout`)}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowFlowCanvas((current) => !current)}
            data-testid="skill-workbench-toggle-flow"
          >
            {showFlowCanvas ? 'Hide Flow Map' : 'Show Flow Map'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowValidation((current) => !current)}
            data-testid="skill-workbench-toggle-validation"
          >
            {showValidation ? 'Hide Validation' : 'Show Validation'}
          </Button>
          <Button
            onClick={() => void handleSave()}
            disabled={!document || !compiled?.validation.isValid || !dirty || mutations.update.isPending}
            data-testid="skill-workbench-save"
          >
            <Save size={16} />
            {t(`${am}skills.workbench.saveOrchestration`)}
          </Button>
        </div>
      )}
      supporting={(
        <div className="flex flex-wrap items-center gap-3 text-sm text-text-secondary">
          <div>
            <span className="text-text-muted">{t(`${am}skills.workbench.skillKeyLabel`)}</span>
            <span className="font-mono">{skill.skillKey}</span>
          </div>
          <Badge tone={compiled?.validation.isValid ? 'success' : 'danger'}>
            {compiled?.validation.isValid
              ? t(`${am}skills.workbench.validationValid`)
              : t(`${am}skills.workbench.validationInvalid`)}
          </Badge>
          <Badge tone={dirty ? 'warning' : 'neutral'}>
            {dirty ? t(`${am}skills.workbench.unsavedChanges`) : t(`${am}skills.workbench.synced`)}
          </Badge>
          <div>
            <span className="text-text-muted">{t(`${am}skills.workbench.versionLabel`)}</span>
            <span className="font-mono">{skill.version}</span>
          </div>
        </div>
      )}
    >
      <div className="flex min-h-0 flex-1 flex-col gap-4">
        {pendingRemoteUpdate ? (
          <div data-testid="skill-workbench-remote-update">
            <Card className="border-primary/20 bg-primary/5" bodyClassName="p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <InlineMessage tone="info">{t(`${am}skills.workbench.remoteUpdateMessage`)}</InlineMessage>
                <div className="flex justify-end">
                  <Button
                    variant="secondary"
                    onClick={handleApplyRemoteVersion}
                    data-testid="skill-workbench-apply-remote"
                  >
                    {t(`${am}skills.workbench.applyRemoteVersion`)}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        ) : null}

        {(mutations.update.error || error) ? (
          <InlineMessage tone="error">
            {mutations.update.error ? mutations.getMutationMessage(mutations.update.error) : error}
          </InlineMessage>
        ) : null}

        {document && compiled ? (
          <div
            className={cn(
              'grid min-h-0 flex-1 gap-4 xl:grid-cols-[18rem_minmax(0,1fr)]',
              auxPanelCount > 0 && 'xl:grid-cols-[18rem_minmax(0,1fr)_20rem]',
            )}
          >
            <div data-testid="skill-workbench-outline-panel">
              <Card
                title={t(`${am}skills.workbench.outlinePanel`)}
                className="flex h-full min-h-0 flex-col"
                bodyClassName="min-h-0 flex-1 overflow-hidden"
              >
                <div className="h-full overflow-auto pr-1">
                  <SkillFlowOutline
                    document={document}
                    selection={selection}
                    onSelectState={(id) => setSelection(id ? { kind: 'state', id } : null)}
                    onInsertStateBefore={handleAddTaskStateBeforeState}
                    onInsertStateAfter={handleAddTaskStateAfterState}
                    onInsertDecisionAfter={handleAddDecisionAfterState}
                  />
                </div>
              </Card>
            </div>

            <div data-testid="skill-workbench-inspector-panel">
              <Card
                title={t(`${am}skills.workbench.inspectorPanel`)}
                className="flex h-full min-h-0 flex-col"
                bodyClassName="min-h-0 flex-1 overflow-hidden"
              >
                <div className="h-full overflow-auto pr-1">
                  <SkillFlowInspector
                    document={document}
                    selection={selection}
                    toolLibrary={toolLibrary}
                    validation={compiled.validation}
                    onAddBranch={handleAddBranchToDecisionState}
                    onAddTaskBranch={handleAddTaskBranch}
                    onAddTool={addToolToTaskState}
                    onDeleteState={deleteState}
                    onRemoveTool={removeToolFromTaskState}
                    onUpdateDecisionState={updateDecisionState}
                    onUpdateHandoffState={updateHandoffState}
                    onUpdateTaskState={updateTaskState}
                    onUpdateTerminalState={updateTerminalState}
                    onUpdateToolPlanReason={updateToolPlanReason}
                    onUpdateTransition={updateTransition}
                  />
                </div>
              </Card>
            </div>

            {auxPanelCount > 0 ? (
              <div
                className={cn(
                  'grid min-h-0 gap-4',
                  auxPanelCount > 1 ? 'xl:grid-rows-[minmax(0,1fr)_16rem]' : 'grid-rows-[minmax(0,1fr)]',
                )}
              >
                {showFlowCanvas ? (
                  <div data-testid="skill-workbench-canvas-panel">
                    <Card
                      title={t(`${am}skills.workbench.canvasPanel`)}
                      className="flex h-full min-h-0 flex-col"
                      bodyClassName="min-h-0 flex-1 overflow-hidden"
                    >
                      <SkillFlowCanvas
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onSelectState={(id) => setSelection(id ? { kind: 'state', id } : null)}
                        onSelectTransition={(id) => setSelection(id ? { kind: 'transition', id } : null)}
                      />
                    </Card>
                  </div>
                ) : null}

                {showValidation ? (
                  <div data-testid="skill-workbench-validation-panel">
                    <Card
                      title={t(`${am}skills.workbench.validationPanel`)}
                      className="flex h-full min-h-0 flex-col"
                      bodyClassName="min-h-0 flex-1 overflow-hidden"
                    >
                      <div className="h-full overflow-auto pr-1">
                        <SkillFlowValidationPanel validation={compiled.validation} />
                      </div>
                    </Card>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </PageFrame>
  );
}

export function SkillWorkbenchPage() {
  const { skillKey = '' } = useParams<{ skillKey: string }>();

  return (
    <SkillFlowBuilderStoreProvider key={skillKey}>
      <SkillWorkbenchPageContent skillKey={skillKey} />
    </SkillFlowBuilderStoreProvider>
  );
}
