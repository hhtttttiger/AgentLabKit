import { describe, expect, it } from 'vitest';
import {
  defaultSkillFilters,
  filterSkillRows,
  mapSkillDefinition,
  toSkillDefinitionApiCreateRequest,
  toSkillDefinitionApiUpdateRequest,
  toSkillListQuery,
} from './types';

describe('skill type helpers', () => {
  it('only sends publishedOnly when filtering published rows', () => {
    expect(toSkillListQuery(defaultSkillFilters)).toEqual({});
    expect(toSkillListQuery({ ...defaultSkillFilters, status: 'published' })).toEqual({ publishedOnly: true });
  });

  it('maps backend spec into structured draft fields', () => {
    const result = mapSkillDefinition({
      id: '1',
      skillKey: 'summarize',
      displayName: 'Summarize',
      description: 'summarize docs',
      version: '1.0.0',
      spec: {
        tags: ['nlp'],
        promptSections: [{ key: 'system', content: 'foo', sortOrder: 0 }],
        toolBindings: [{ toolName: 'search_docs', invocationMode: 'auto', isEnabled: true }],
        configSchema: { type: 'object' },
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            done: {
              id: 'done',
              kind: 'terminal',
              title: 'Done',
              outcome: 'resolved',
              resolutionNote: 'done',
            },
          },
          transitions: {},
        },
      },
      isPublished: true,
      createdAtUtc: '2026-04-08T00:00:00Z',
      updatedAtUtc: null,
    });

    expect(result.status).toBe('published');
    expect(result.tags).toEqual(['nlp']);
    expect(result.promptSections[0]?.key).toBe('system');
    expect(result.toolBindings[0]?.toolName).toBe('search_docs');
    expect(result.orchestration?.entryStateId).toBe('start');
  });

  it('drops malformed orchestration payloads instead of passing partial graph data downstream', () => {
    const result = mapSkillDefinition({
      id: '1',
      skillKey: 'summarize',
      displayName: 'Summarize',
      description: 'summarize docs',
      version: '1.0.0',
      spec: {
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            broken: {
              id: 'broken',
              kind: 'task',
              title: 'Broken task',
              goal: 'missing required nested contracts',
            },
          },
          transitions: {},
        },
      },
      isPublished: false,
      createdAtUtc: '2026-04-08T00:00:00Z',
      updatedAtUtc: null,
    });

    expect(result.orchestration).toBeNull();
  });

  it('serializes the structured draft back to backend spec', () => {
    expect(
      toSkillDefinitionApiCreateRequest({
        skillKey: 'summarize',
        displayName: 'Summarize',
        description: 'summarize docs',
        version: '1.0.0',
        tags: ['nlp'],
        promptSections: [{ key: 'system', content: 'foo', sortOrder: 0 }],
        toolBindings: [],
        configSchema: { type: 'object' },
        spec: {},
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            done: {
              id: 'done',
              kind: 'terminal',
              title: 'Done',
              outcome: 'resolved',
              resolutionNote: 'done',
            },
          },
          transitions: {},
        },
      }),
    ).toEqual({
      skillKey: 'summarize',
      displayName: 'Summarize',
      description: 'summarize docs',
      version: '1.0.0',
      spec: {
        tags: ['nlp'],
        promptSections: [{ key: 'system', content: 'foo', sortOrder: 0 }],
        toolBindings: [],
        configSchema: { type: 'object' },
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            done: {
              id: 'done',
              kind: 'terminal',
              title: 'Done',
              outcome: 'resolved',
              resolutionNote: 'done',
            },
          },
          transitions: {},
        },
      },
    });
  });

  it('preserves existing orchestration metadata when updating non-workbench fields', () => {
    expect(
      toSkillDefinitionApiUpdateRequest({
        displayName: 'Summarize v2',
        description: 'summarize docs better',
        version: '1.1.0',
        tags: ['nlp'],
        promptSections: [],
        toolBindings: [],
        configSchema: {},
        spec: {
          custom: { owner: 'ops' },
          orchestration: {
            version: '3',
            entryStateId: 'start',
            metadata: {
              skillKey: 'summarize',
              displayName: 'Summarize',
              description: 'summarize docs',
              version: '1.0.0',
            },
            states: {
              start: { id: 'start', kind: 'start', title: 'Start' },
              done: {
                id: 'done',
                kind: 'terminal',
                title: 'Done',
                outcome: 'resolved',
                resolutionNote: 'done',
              },
            },
            transitions: {},
          },
        },
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            done: {
              id: 'done',
              kind: 'terminal',
              title: 'Done',
              outcome: 'resolved',
              resolutionNote: 'done',
            },
          },
          transitions: {},
        },
      }),
    ).toEqual({
      displayName: 'Summarize v2',
      description: 'summarize docs better',
      version: '1.1.0',
      spec: {
        custom: { owner: 'ops' },
        tags: ['nlp'],
        promptSections: [],
        toolBindings: [],
        configSchema: {},
        orchestration: {
          version: '3',
          entryStateId: 'start',
          metadata: {
            skillKey: 'summarize',
            displayName: 'Summarize',
            description: 'summarize docs',
            version: '1.0.0',
          },
          states: {
            start: { id: 'start', kind: 'start', title: 'Start' },
            done: {
              id: 'done',
              kind: 'terminal',
              title: 'Done',
              outcome: 'resolved',
              resolutionNote: 'done',
            },
          },
          transitions: {},
        },
      },
    });
  });

  it('filters rows locally by status, tag, and search', () => {
    const result = filterSkillRows([
      {
        id: '1',
        skillKey: 'summarize',
        displayName: 'Summarize',
        description: 'summarize docs',
        version: '1.0.0',
        status: 'published',
        tags: ['nlp'],
        promptSections: [],
        toolBindings: [],
        configSchema: {},
        spec: {},
        orchestration: null,
        createdAtUtc: '',
        updatedAtUtc: null,
      },
      {
        id: '2',
        skillKey: 'draft-skill',
        displayName: 'Draft Skill',
        description: 'beta',
        version: '0.1.0',
        status: 'draft',
        tags: ['internal'],
        promptSections: [],
        toolBindings: [],
        configSchema: {},
        spec: {},
        orchestration: null,
        createdAtUtc: '',
        updatedAtUtc: null,
      },
    ], {
      ...defaultSkillFilters,
      status: 'draft',
      tag: 'internal',
      search: 'beta',
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.skillKey).toBe('draft-skill');
  });
});
