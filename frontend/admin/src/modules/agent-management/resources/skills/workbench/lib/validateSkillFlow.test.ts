import { describe, expect, test } from 'vitest';
import type { SkillFlowDocument, TaskState } from './types';
import { validateSkillFlow } from './validateSkillFlow';

function buildValidFlow(): SkillFlowDocument {
  return {
    version: '3',
    metadata: {
      skillKey: 'refund-orchestration',
      displayName: '退款编排',
      description: '退款路由流程',
      version: '1.0.0',
    },
    entryStateId: 'start',
    states: {
      start: { id: 'start', kind: 'start', title: '开始' },
      intake: {
        id: 'intake',
        kind: 'task',
        title: '收集上下文',
        goal: '收集退款上下文',
        toolPlan: [{ id: 'plan-status', toolId: 'query_refund_status', reason: '读取退款状态' }],
        inputContract: {
          inherited: [],
          required: [{ key: 'user_intent', label: '用户意图' }],
          optional: [],
        },
        outputContract: [{ key: 'refund_context', label: '退款上下文' }],
        fallbackPolicy: { mode: 'stay', note: '继续补充信息' },
      },
      routing: {
        id: 'routing',
        kind: 'decision',
        title: '选择路径',
        question: '走自动处理还是转人工？',
      },
      status: {
        id: 'status',
        kind: 'task',
        title: '读取状态',
        goal: '读取当前退款状态',
        toolPlan: [{ id: 'plan-status-query', toolId: 'query_refund_status', reason: '读取当前状态' }],
        inputContract: {
          inherited: [{ key: 'refund_context', label: '退款上下文' }],
          required: [],
          optional: [],
        },
        outputContract: [{ key: 'status_result', label: '状态结果' }],
        fallbackPolicy: { mode: 'goto', transitionId: 'status-fallback', note: '失败时转人工' },
      },
      ticket: {
        id: 'ticket',
        kind: 'task',
        title: '创建退款工单',
        goal: '提交退款执行请求',
        toolPlan: [{ id: 'plan-ticket', toolId: 'create_refund_ticket', reason: '创建退款工单' }],
        inputContract: {
          inherited: [{ key: 'refund_context', label: '退款上下文' }],
          required: [{ key: 'refund_reason', label: '退款原因' }],
          optional: [],
        },
        outputContract: [{ key: 'ticket_id', label: '工单编号' }],
        fallbackPolicy: { mode: 'stay', note: '继续补充信息' },
      },
      handoff: {
        id: 'handoff',
        kind: 'handoff',
        title: '转人工',
        handoffType: 'human',
        summaryTemplate: '转交人工客服处理',
      },
      resolved: {
        id: 'resolved',
        kind: 'terminal',
        title: '已解决',
        outcome: 'resolved',
        resolutionNote: '流程完成',
      },
    },
    transitions: {
      'start-to-intake': {
        id: 'start-to-intake',
        fromStateId: 'start',
        toStateId: 'intake',
        label: '开始',
        kind: 'default',
        priority: 0,
      },
      'intake-to-routing': {
        id: 'intake-to-routing',
        fromStateId: 'intake',
        toStateId: 'routing',
        label: '继续',
        kind: 'default',
        priority: 0,
      },
      'to-status': {
        id: 'to-status',
        fromStateId: 'routing',
        toStateId: 'status',
        label: '查询状态',
        kind: 'condition',
        priority: 0,
        predicate: {
          description: '状态查询请求',
          expression: { field: 'intent_type', operator: 'eq', value: 'status' },
        },
      },
      'to-ticket': {
        id: 'to-ticket',
        fromStateId: 'routing',
        toStateId: 'ticket',
        label: '执行退款',
        kind: 'condition',
        priority: 1,
        predicate: {
          description: '执行退款请求',
          expression: { field: 'intent_type', operator: 'eq', value: 'execute' },
        },
      },
      'to-handoff': {
        id: 'to-handoff',
        fromStateId: 'routing',
        toStateId: 'handoff',
        label: '转人工',
        kind: 'handoff',
        priority: 2,
      },
      'status-to-resolved': {
        id: 'status-to-resolved',
        fromStateId: 'status',
        toStateId: 'resolved',
        label: '状态完成',
        kind: 'default',
        priority: 0,
      },
      'status-fallback': {
        id: 'status-fallback',
        fromStateId: 'status',
        toStateId: 'handoff',
        label: '状态查询失败',
        kind: 'fallback',
        priority: 1,
      },
      'ticket-to-resolved': {
        id: 'ticket-to-resolved',
        fromStateId: 'ticket',
        toStateId: 'resolved',
        label: '工单创建完成',
        kind: 'default',
        priority: 0,
      },
    },
  };
}

describe('validateSkillFlow', () => {
  test('accepts a branched flow with a decision node and terminal outcome', () => {
    const result = validateSkillFlow(buildValidFlow());

    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  test('rejects a missing entry state or non-start entry state', () => {
    const missingEntry = buildValidFlow();
    missingEntry.entryStateId = 'missing';

    expect(validateSkillFlow(missingEntry).errors).toContain('入口节点 "missing" 不存在。');

    const wrongKind = buildValidFlow();
    wrongKind.entryStateId = 'intake';

    expect(validateSkillFlow(wrongKind).errors).toContain('入口节点 "intake" 必须指向开始节点。');
  });

  test('rejects orphan states and decision nodes with fewer than two outgoing transitions', () => {
    const flow = buildValidFlow();
    flow.states.orphan = {
      id: 'orphan',
      kind: 'terminal',
      title: '孤立节点',
      outcome: 'blocked',
      resolutionNote: 'Should not be reachable',
    };
    delete flow.transitions['to-ticket'];
    delete flow.transitions['to-handoff'];

    const result = validateSkillFlow(flow);

    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('判断节点 "routing" 至少需要 2 条外出流转。');
    expect(result.errors).toContain('节点 "orphan" 无法从入口节点 "start" 到达。');
  });

  test('rejects duplicate branch priorities on a decision state', () => {
    const flow = buildValidFlow();
    flow.transitions['to-ticket'] = { ...flow.transitions['to-ticket'], priority: 0 };

    expect(validateSkillFlow(flow).errors).toContain('判断节点 "routing" 存在重复的流转优先级 "0"。');
  });

  test('rejects task nodes without exactly one default outgoing transition', () => {
    const flow = buildValidFlow();
    delete flow.transitions['status-to-resolved'];

    expect(validateSkillFlow(flow).errors).toContain('任务节点 "status" 必须保留 1 条默认流转。');

    flow.transitions['status-to-resolved'] = {
      id: 'status-to-resolved',
      fromStateId: 'status',
      toStateId: 'resolved',
      label: '状态完成',
      kind: 'default',
      priority: 0,
    };
    flow.transitions['status-to-ticket'] = {
      id: 'status-to-ticket',
      fromStateId: 'status',
      toStateId: 'ticket',
      label: '再次执行',
      kind: 'default',
      priority: 2,
    };

    expect(validateSkillFlow(flow).errors).toContain('任务节点 "status" 必须保留 1 条默认流转。');
  });

  test('rejects goto fallback policies that do not point to an outgoing fallback transition', () => {
    const flow = buildValidFlow();
    const statusState = flow.states.status as TaskState;
    flow.states.status = {
      ...statusState,
      fallbackPolicy: { mode: 'goto', transitionId: 'ticket-to-resolved', note: 'bad fallback' },
    };

    expect(validateSkillFlow(flow).errors).toContain(
      '任务节点 "status" 的 goto 兜底流转 "ticket-to-resolved" 必须是当前节点发出的 fallback 流转。',
    );
  });

  test('rejects terminal states with outgoing transitions', () => {
    const flow = buildValidFlow();
    flow.transitions['resolved-to-ticket'] = {
      id: 'resolved-to-ticket',
      fromStateId: 'resolved',
      toStateId: 'ticket',
      label: '非法重试',
      kind: 'default',
      priority: 0,
    };

    expect(validateSkillFlow(flow).errors).toContain('结束节点 "resolved" 不能再有外出流转。');
  });
});
