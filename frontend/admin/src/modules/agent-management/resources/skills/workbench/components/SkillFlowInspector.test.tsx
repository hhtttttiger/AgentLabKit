import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SkillFlowInspector } from './SkillFlowInspector';
import type { SkillFlowDocument } from '../lib/types';

const document: SkillFlowDocument = {
  version: '3',
  metadata: {
    skillKey: 'refund-routing',
    displayName: '退款分流',
    description: '退款技能编排',
    version: '1.0.0',
  },
  entryStateId: 'start',
  states: {
    start: { id: 'start', kind: 'start', title: '开始' },
    intake: {
      id: 'intake',
      kind: 'task',
      title: '收集上下文',
      goal: '收集退款请求信息',
      toolPlan: [
        {
          id: 'plan-status',
          toolId: 'query_refund_status',
          reason: '先确认当前退款状态。',
        },
      ],
      inputContract: {
        inherited: [{ key: 'session_id', label: '会话标识' }],
        required: [{ key: 'order_id', label: '订单号' }],
        optional: [{ key: 'refund_reason', label: '退款原因' }],
      },
      outputContract: [{ key: 'refund_context', label: '退款上下文' }],
      fallbackPolicy: { mode: 'goto', transitionId: 'intake-fallback', note: '无法完成时进入兜底分支。' },
    },
    route: {
      id: 'route',
      kind: 'decision',
      title: '判断去向',
      question: '应该继续处理还是转人工？',
    },
    handoff: {
      id: 'handoff',
      kind: 'handoff',
      title: '转人工处理',
      handoffType: 'human',
      summaryTemplate: '请汇总退款背景后转交人工客服。',
    },
    done: {
      id: 'done',
      kind: 'terminal',
      title: '处理完成',
      outcome: 'resolved',
      resolutionNote: '退款流程已完成。',
    },
  },
  transitions: {
    'start-intake': {
      id: 'start-intake',
      fromStateId: 'start',
      toStateId: 'intake',
      label: '开始',
      kind: 'default',
      priority: 0,
    },
    'intake-route': {
      id: 'intake-route',
      fromStateId: 'intake',
      toStateId: 'route',
      label: '进入判断',
      kind: 'default',
      priority: 0,
    },
    'intake-fallback': {
      id: 'intake-fallback',
      fromStateId: 'intake',
      toStateId: 'handoff',
      label: '兜底转人工',
      kind: 'fallback',
      priority: 1,
    },
    'route-done': {
      id: 'route-done',
      fromStateId: 'route',
      toStateId: 'done',
      label: '自动处理',
      kind: 'condition',
      priority: 0,
      predicate: {
        description: '信息完整时自动处理',
        expression: { field: 'resolution', operator: 'eq', value: 'auto' },
      },
    },
    'route-handoff': {
      id: 'route-handoff',
      fromStateId: 'route',
      toStateId: 'handoff',
      label: '转人工',
      kind: 'handoff',
      priority: 1,
    },
  },
};

describe('SkillFlowInspector', () => {
  it('renders task authoring fields in the Chinese product language', () => {
    render(
      <SkillFlowInspector
        document={document}
        selection={{ kind: 'state', id: 'intake' }}
        toolLibrary={[
          {
            id: 'query_refund_status',
            name: '查询退款状态',
            description: '读取退款状态',
            isEnabled: true,
            isRequired: false,
            config: {},
          },
        ]}
        validation={{ isValid: true, errors: [], warnings: [] }}
        onAddTool={vi.fn()}
        onRemoveTool={vi.fn()}
        onUpdateTaskState={vi.fn()}
        onUpdateToolPlanReason={vi.fn()}
        onAddTaskBranch={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('步骤标题')).toBeInTheDocument();
    expect(screen.getByLabelText('继承输入')).toBeInTheDocument();
    expect(screen.getByLabelText('必填输入')).toBeInTheDocument();
    expect(screen.getByLabelText('可选输入')).toBeInTheDocument();
    expect(screen.getByLabelText('兜底策略')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增兜底分支' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增异常分支' })).toBeInTheDocument();
  });

  it('renders editable transition fields instead of read-only labels', () => {
    render(
      <SkillFlowInspector
        document={document}
        selection={{ kind: 'transition', id: 'route-done' }}
        toolLibrary={[]}
        validation={{ isValid: true, errors: [], warnings: [] }}
        onAddTool={vi.fn()}
        onRemoveTool={vi.fn()}
        onUpdateTaskState={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('流转名称')).toBeInTheDocument();
    expect(screen.getByLabelText('流转类型')).toBeInTheDocument();
    expect(screen.getByLabelText('命中条件说明')).toBeInTheDocument();
  });
});
