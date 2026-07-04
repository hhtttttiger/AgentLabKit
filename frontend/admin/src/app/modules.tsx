import { Activity, Blocks, BookOpen, Bot, Brain, Database, DollarSign, FlaskConical, MessageSquare, Search, type LucideIcon } from 'lucide-react';
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

export type ModuleKey = 'ai-chat' | 'agent-management' | 'model-management' | 'glossary' | 'knowledge-base' | 'model-monitoring' | 'cost-analysis' | 'observability' | 'memory' | 'evaluation';

export type ModuleDefinition = {
  key: ModuleKey;
  icon: LucideIcon;
  basePath: string;
};

export const appModules: ModuleDefinition[] = [
  { key: 'ai-chat', icon: MessageSquare, basePath: '/ai-chat' },
  { key: 'agent-management', icon: Bot, basePath: '/agent-management' },
  { key: 'model-management', icon: Blocks, basePath: '/model-management' },
  { key: 'glossary', icon: BookOpen, basePath: '/glossary' },
  { key: 'knowledge-base', icon: Database, basePath: '/knowledge-base' },
  { key: 'model-monitoring', icon: Activity, basePath: '/model-monitoring' },
  { key: 'cost-analysis', icon: DollarSign, basePath: '/cost-analysis' },
  { key: 'observability', icon: Search, basePath: '/observability' },
  { key: 'memory', icon: Brain, basePath: '/memory' },
  { key: 'evaluation', icon: FlaskConical, basePath: '/evaluation' },
];

export const moduleRoutes = [
  ...aiChatRoutes, ...agentManagementRoutes, ...modelManagementRoutes,
  ...glossaryRoutes, ...knowledgeBaseRoutes, ...modelMonitoringRoutes,
  ...costAnalysisRoutes, ...observabilityRoutes, ...memoryRoutes,
  ...evaluationRoutes,
];
