import { Activity, Blocks, BookOpen, Bot, Brain, Database, DollarSign, FlaskConical, MessageSquare, Puzzle, Search, Timer, Users, type LucideIcon } from 'lucide-react';
import { agentManagementRoutes } from '@/modules/agent-management/routes';
import { modelManagementRoutes } from '@/modules/model-management/routes';
import { modelMonitoringRoutes } from '@/modules/model-monitoring/routes';
import { aiChatRoutes } from '@/modules/ai-chat/routes';
import { glossaryRoutes } from '@/modules/glossary/routes';
import { knowledgeBaseRoutes } from '@/modules/knowledge-base/routes';
import { costAnalysisRoutes } from '@/modules/cost-analysis/routes';
import { observabilityRoutes } from '@/modules/observability/routes';
import { memoryRoutes } from '@/modules/memory/routes';
import { evaluationRoutes } from '@/modules/evaluation/routes';
import { userManagementRoutes } from '@/modules/user-management/routes';
import { overviewRoutes } from '@/modules/overview/routes';
import { runsRoutes } from '@/modules/runs/routes';
import { capabilitiesRoutes } from '@/modules/capabilities/routes';

export type ModuleKey = 'ai-chat' | 'agent-management' | 'model-management' | 'glossary' | 'knowledge-base' | 'model-monitoring' | 'cost-analysis' | 'observability' | 'memory' | 'evaluation' | 'user-management' | 'runs' | 'capabilities';

export type ModuleGroup = 'build' | 'run' | 'improve' | 'platform';

export type ModuleDefinition = {
  key: ModuleKey;
  icon: LucideIcon;
  basePath: string;
  group: ModuleGroup;
  order: number;
};

export const appModules: ModuleDefinition[] = [
  // BUILD
  { key: 'agent-management', icon: Bot, basePath: '/agents', group: 'build', order: 1 },
  { key: 'capabilities', icon: Puzzle, basePath: '/capabilities', group: 'build', order: 2 },
  { key: 'knowledge-base', icon: Database, basePath: '/knowledge', group: 'build', order: 3 },
  { key: 'model-management', icon: Blocks, basePath: '/models', group: 'build', order: 4 },

  // RUN
  { key: 'ai-chat', icon: MessageSquare, basePath: '/playground', group: 'run', order: 1 },
  { key: 'runs', icon: Timer, basePath: '/runs', group: 'run', order: 2 },

  // IMPROVE
  { key: 'observability', icon: Search, basePath: '/traces', group: 'improve', order: 1 },
  { key: 'evaluation', icon: FlaskConical, basePath: '/evaluation', group: 'improve', order: 2 },
  { key: 'cost-analysis', icon: DollarSign, basePath: '/cost', group: 'improve', order: 3 },

  // PLATFORM
  { key: 'glossary', icon: BookOpen, basePath: '/glossary', group: 'platform', order: 1 },
  { key: 'memory', icon: Brain, basePath: '/memory', group: 'platform', order: 2 },
  { key: 'model-monitoring', icon: Activity, basePath: '/monitoring', group: 'platform', order: 3 },
  { key: 'user-management', icon: Users, basePath: '/users', group: 'platform', order: 4 },
];

export const moduleRoutes = [
  ...overviewRoutes,
  ...aiChatRoutes, ...agentManagementRoutes, ...modelManagementRoutes,
  ...glossaryRoutes, ...knowledgeBaseRoutes, ...modelMonitoringRoutes,
  ...costAnalysisRoutes, ...observabilityRoutes, ...memoryRoutes,
  ...evaluationRoutes, ...userManagementRoutes,
  ...runsRoutes,
  ...capabilitiesRoutes,
];

// Group labels for sidebar rendering
export const moduleGroupLabels: Record<ModuleGroup, string> = {
  build: 'nav.group.build',
  run: 'nav.group.run',
  improve: 'nav.group.improve',
  platform: 'nav.group.platform',
};

// Get modules grouped by their group
export function getModulesByGroup(): Map<ModuleGroup, ModuleDefinition[]> {
  const grouped = new Map<ModuleGroup, ModuleDefinition[]>();
  for (const module of appModules) {
    const existing = grouped.get(module.group) ?? [];
    existing.push(module);
    grouped.set(module.group, existing);
  }
  // Sort within each group by order
  for (const modules of grouped.values()) {
    modules.sort((a, b) => a.order - b.order);
  }
  return grouped;
}
