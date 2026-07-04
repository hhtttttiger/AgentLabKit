import { describe, expect, it } from 'vitest';
import {
  buildWorkbenchToolLibrary,
  createDefaultSkillFlowDocument,
} from './documents';

describe('documents helpers', () => {
  it('filters out disabled tools from metadata and explicit flags', () => {
    const result = buildWorkbenchToolLibrary([
      {
        toolName: 'enabled-tool',
        displayName: 'Enabled Tool',
        description: null,
        invocationMode: 'auto',
        isRequired: false,
        config: {},
        sortOrder: 0,
        isEnabled: true,
      },
      {
        toolName: 'invocation-disabled',
        displayName: 'Disabled by mode',
        description: null,
        invocationMode: 'disabled',
        isRequired: false,
        config: {},
        sortOrder: 1,
        isEnabled: true,
      },
      {
        toolName: 'flag-disabled',
        displayName: 'Disabled by flag',
        description: null,
        invocationMode: 'auto',
        isRequired: false,
        config: {},
        sortOrder: 2,
        isEnabled: false,
      },
    ]);

    expect(result.map((tool) => tool.id)).toEqual(['enabled-tool']);
  });

  it('creates a localized default skill flow document for the Chinese admin product', () => {
    const result = createDefaultSkillFlowDocument({
      skillKey: 'summarize',
      displayName: '文档总结',
      description: '总结文档要点',
      version: '1.0.0',
    });

    expect(result.states.start.title).toBe('开始');
    expect(result.states.analyze).toMatchObject({
      kind: 'task',
      title: '分析请求',
      goal: '总结文档要点',
    });
    expect(result.states.done).toMatchObject({
      kind: 'terminal',
      title: '完成',
      resolutionNote: '流程已完成。',
    });
    expect(result.transitions['start-analyze'].label).toBe('开始');
    expect(result.transitions['analyze-done'].label).toBe('完成');
  });
});
