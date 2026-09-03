import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const AgentManagementLayout = lazyRoute(() => import('./pages/AgentManagementLayout'), 'AgentManagementLayout');
const AgentsPage = lazyRoute(() => import('./resources/agents/AgentsPage'), 'AgentsPage');
const AgentDetailPage = lazyRoute(() => import('./resources/agents/AgentDetailPage'), 'AgentDetailPage');

export const agentManagementRoutes: RouteObject[] = [
  // Primary route — Agents only (Tools/Skills/MCP moved to /capabilities)
  {
    path: 'agents',
    element: routeElement(AgentManagementLayout),
    children: [
      { index: true, element: routeElement(AgentsPage) },
    ],
  },
  // Detail page renders its own nav bar (outside the module layout shell)
  {
    path: 'agents/:agentKey',
    element: routeElement(AgentDetailPage),
  },
  // Legacy route aliases for backward compatibility
  {
    path: 'agent-management',
    element: <Navigate replace to="/agents" />,
  },
  {
    path: 'agent-management/agents',
    element: <Navigate replace to="/agents" />,
  },
  {
    path: 'agent-management/tools',
    element: <Navigate replace to="/capabilities/tools" />,
  },
  {
    path: 'agent-management/skills',
    element: <Navigate replace to="/capabilities/skills" />,
  },
  {
    path: 'agent-management/mcp-servers',
    element: <Navigate replace to="/capabilities/mcp" />,
  },
  {
    path: 'agent-management/*',
    element: <Navigate replace to="/agents" />,
  },
];
