/**
 * Capabilities Module - Routes
 *
 * Reorganizes Tools, Skills, and MCP Servers under a unified "Capabilities" concept.
 * Global: /capabilities/tools, /capabilities/skills, /capabilities/mcp
 */

import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

// Reuse existing pages from agent-management module
const CapabilitiesLayout = lazyRoute(() => import('./pages/CapabilitiesLayout'), 'CapabilitiesLayout');
const ToolsPage = lazyRoute(() => import('@/modules/agent-management/resources/tools/ToolsPage'), 'ToolsPage');
const SkillsPage = lazyRoute(() => import('@/modules/agent-management/resources/skills/SkillsPage'), 'SkillsPage');
const SkillWorkbenchPage = lazyRoute(() => import('@/modules/agent-management/resources/skills/SkillWorkbenchPage'), 'SkillWorkbenchPage');
const McpServersPage = lazyRoute(() => import('@/modules/agent-management/resources/mcp-servers/McpServersPage'), 'McpServersPage');

export const capabilitiesRoutes: RouteObject[] = [
  {
    path: 'capabilities',
    element: routeElement(CapabilitiesLayout),
    children: [
      { index: true, element: <Navigate replace to="/capabilities/tools" /> },
      { path: 'tools', element: routeElement(ToolsPage) },
      { path: 'skills', element: routeElement(SkillsPage) },
      { path: 'skills/:skillKey/workbench', element: routeElement(SkillWorkbenchPage) },
      { path: 'mcp', element: routeElement(McpServersPage) },
    ],
  },
];
