import { BookOpen, ClipboardList, Database, FlaskConical, Home, Settings, Timer, type LucideIcon } from 'lucide-react';
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
import { sessionsRoutes } from '@/modules/sessions/routes';
import { settingsRoutes } from '@/modules/settings/routes';

export type ModuleKey = 'home' | 'sessions' | 'runs' | 'datasets' | 'evaluation' | 'knowledge-base' | 'settings';

export type ModuleGroup = 'build' | 'run' | 'improve' | 'platform';

export type ModuleDefinition = {
  key: ModuleKey;
  icon: LucideIcon;
  basePath: string;
  group: ModuleGroup;
  order: number;
};

export const appModules: ModuleDefinition[] = [
  { key: 'home', icon: Home, basePath: '/overview', group: 'build', order: 1 },
  { key: 'sessions', icon: ClipboardList, basePath: '/sessions', group: 'run', order: 1 },
  { key: 'runs', icon: Timer, basePath: '/runs', group: 'run', order: 2 },
  { key: 'datasets', icon: Database, basePath: '/evaluation/datasets', group: 'improve', order: 1 },
  { key: 'evaluation', icon: FlaskConical, basePath: '/evaluation', group: 'improve', order: 2 },
  { key: 'knowledge-base', icon: BookOpen, basePath: '/knowledge', group: 'platform', order: 1 },
  { key: 'settings', icon: Settings, basePath: '/settings', group: 'platform', order: 2 },
];

export const moduleRoutes = [
  ...overviewRoutes,
  ...aiChatRoutes, ...agentManagementRoutes, ...modelManagementRoutes,
  ...glossaryRoutes, ...knowledgeBaseRoutes, ...modelMonitoringRoutes,
  ...costAnalysisRoutes, ...observabilityRoutes, ...memoryRoutes,
  ...evaluationRoutes, ...userManagementRoutes,
  ...runsRoutes,
  ...sessionsRoutes,
  ...capabilitiesRoutes,
  ...settingsRoutes,
];

// Group labels for sidebar rendering
export const moduleGroupLabels: Record<ModuleGroup, string> = {
  build: 'Workspace',
  run: 'Work',
  improve: 'Engineering',
  platform: 'Context',
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
