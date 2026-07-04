export const agentManagementQueryKeys = {
  agentsRoot: () => ['agent-management', 'agents'] as const,
  agents: (suffix: string, query?: unknown) => ['agent-management', 'agents', suffix, query] as const,
  versionsRoot: (agentKey: string) => ['agent-management', 'versions', agentKey] as const,
  versions: (agentKey: string, suffix: string, query?: unknown) => ['agent-management', 'versions', agentKey, suffix, query] as const,
  knowledgeBaseBindingsRoot: (agentKey: string) => ['agent-management', 'knowledge-base-bindings', agentKey] as const,
  knowledgeBaseBindings: (agentKey: string, suffix: string, query?: unknown) =>
    ['agent-management', 'knowledge-base-bindings', agentKey, suffix, query] as const,
  audits: (agentKey: string, suffix: string, query?: unknown) => ['agent-management', 'audits', agentKey, suffix, query] as const,
  mcpServersRoot: () => ['agent-management', 'mcp-servers'] as const,
  mcpServers: (suffix: string, query?: unknown) => ['agent-management', 'mcp-servers', suffix, query] as const,
  skillsRoot: () => ['agent-management', 'skills'] as const,
  skills: (suffix: string, query?: unknown) => ['agent-management', 'skills', suffix, query] as const,
  toolsRoot: () => ['agent-management', 'tools'] as const,
  tools: (suffix: string, query?: unknown) => ['agent-management', 'tools', suffix, query] as const,
};
