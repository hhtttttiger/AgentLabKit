import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const AgentManagementLayout = lazyRoute(() => import('./pages/AgentManagementLayout'), 'AgentManagementLayout');
const AgentsPage = lazyRoute(() => import('./resources/agents/AgentsPage'), 'AgentsPage');
const AgentDetailPage = lazyRoute(() => import('./resources/agents/AgentDetailPage'), 'AgentDetailPage');
const McpServersPage = lazyRoute(() => import('./resources/mcp-servers/McpServersPage'), 'McpServersPage');
const SkillsPage = lazyRoute(() => import('./resources/skills/SkillsPage'), 'SkillsPage');
const SkillWorkbenchPage = lazyRoute(() => import('./resources/skills/SkillWorkbenchPage'), 'SkillWorkbenchPage');
const ToolsPage = lazyRoute(() => import('./resources/tools/ToolsPage'), 'ToolsPage');

export const agentManagementRoutes: RouteObject[] = [
  {
    path: 'agent-management',
    element: routeElement(AgentManagementLayout),
    children: [
      { index: true, element: <Navigate replace to="/agent-management/agents" /> },
      { path: 'agents', element: routeElement(AgentsPage) },
      { path: 'tools', element: routeElement(ToolsPage) },
      { path: 'skills', element: routeElement(SkillsPage) },
      { path: 'skills/:skillKey/workbench', element: routeElement(SkillWorkbenchPage) },
      { path: 'mcp-servers', element: routeElement(McpServersPage) },
    ],
  },
  // Detail page renders its own nav bar (outside the module layout shell)
  {
    path: 'agent-management/agents/:agentKey',
    element: routeElement(AgentDetailPage),
  },
];
