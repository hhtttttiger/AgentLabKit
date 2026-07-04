import { describe, expect, it } from 'vitest';
import type { VersionDetailView } from '../../lib/contracts';
import { emptyVersionDraft } from './types';
import {
  createEmptyMcpBinding,
  createEmptySkillBinding,
  emptyToolOverride,
  ensureVersionDefaultPolicy,
  validateVersionDraft,
  versionDetailToDraft,
} from './draft';

const sampleVersionDetail: VersionDetailView = {
  versionNumber: 3,
  versionStatus: 'draft',
  versionLabel: 'beta',
  changeSummary: 'updated bindings',
  modelKey: 'binding.primary',
  checksum: null,
  rowVersion: 7,
  publishedAtUtc: null,
  createdAtUtc: '2026-04-08T00:00:00Z',
  systemPromptTemplate: 'You are helpful.',
  defaultLocale: 'zh-CN',
  runtimeOptions: {},
  handoffPolicy: {},
  responsePolicy: { mode: 'default' },
  guardrailsPolicy: {},
  toolBindings: [
    {
      toolName: 'search_docs',
      displayName: 'Search Docs',
      description: null,
      invocationMode: 'auto',
      isRequired: false,
      config: { topK: 5 },
      sortOrder: 0,
      isEnabled: true,
    },
  ],
  knowledgeBaseBindings: [{
    id: 'binding-1',
    knowledgeBaseId: 'kb-1',
    sortOrder: 10,
    isEnabled: true,
    config: {},
  }],
  mcpBindings: [{ id: 'mcp-1', serverName: 'workspace', toolWhitelist: ['read_file'], isEnabled: true, configOverrides: {} }],
  skillBindings: [{
    id: 'skill-1',
    skillKey: 'summarize-doc',
    displayName: 'Summarize Doc',
    sortOrder: 0,
    isEnabled: true,
    configOverrides: { style: 'short' },
    toolOverrides: [{
      toolName: 'summarize_tool',
      displayName: 'Summarizer',
      description: null,
      invocationMode: 'manual_only',
      isRequired: true,
      config: { format: 'bullet' },
      sortOrder: 0,
      isEnabled: true,
    }],
  }],
};

describe('version draft helpers', () => {
  it('maps version details into an editable draft without losing nested skill tool overrides', () => {
    const draft = versionDetailToDraft(sampleVersionDetail);

    expect(draft.knowledgeBaseBindings).toEqual([{
      id: 'binding-1',
      knowledgeBaseId: 'kb-1',
      sortOrder: 10,
      isEnabled: true,
      config: {},
    }]);
    expect(draft.mcpBindings).toEqual([{ serverName: 'workspace', toolWhitelist: ['read_file'], isEnabled: true }]);
    expect(draft.skillBindings[0]?.toolOverrides[0]?.toolName).toBe('summarize_tool');
    expect(draft.toolBindings[0]?.config).toEqual({ topK: 5 });
  });

  it('injects the default response policy only when every policy section is empty', () => {
    expect(ensureVersionDefaultPolicy({ ...emptyVersionDraft, responsePolicy: null })).toMatchObject({
      responsePolicy: { mode: 'default' },
    });

    const withRuntimeOptions = ensureVersionDefaultPolicy({
      ...emptyVersionDraft,
      responsePolicy: null,
      runtimeOptions: { timeoutSeconds: 30 },
    });

    expect(withRuntimeOptions.responsePolicy).toBeNull();
    expect(withRuntimeOptions.runtimeOptions).toEqual({ timeoutSeconds: 30 });
  });

  it('validates required MCP, skill, and nested tool override fields', () => {
    const errors = validateVersionDraft({
      ...emptyVersionDraft,
      systemPromptTemplate: 'prompt',
      modelKey: 'binding.primary',
      knowledgeBaseBindings: [
        { id: null, knowledgeBaseId: 'kb-1', sortOrder: 10, isEnabled: true, config: {} },
        { id: null, knowledgeBaseId: 'kb-1', sortOrder: 20, isEnabled: false, config: {} },
      ],
      mcpBindings: [createEmptyMcpBinding()],
      skillBindings: [
        {
          ...createEmptySkillBinding(0),
          toolOverrides: [emptyToolOverride(0)],
        },
      ],
    });

    expect(errors.kb_1_knowledgeBaseId).toContain('重复');
    expect(errors.mcp_0_serverName).toContain('MCP');
    expect(errors.skill_0_skillKey).toContain('技能');
    expect(errors.skill_0_tool_0_toolName).toContain('工具覆盖');
  });
});
