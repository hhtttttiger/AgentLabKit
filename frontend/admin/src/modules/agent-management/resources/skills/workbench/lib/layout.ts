import dagre from 'dagre';
import type { SkillFlowGraphEdge, SkillFlowGraphNode } from './reactFlowAdapters';

export function applyAutoLayoutToSkillFlow(
  nodes: SkillFlowGraphNode[],
  edges: SkillFlowGraphEdge[],
  direction: 'TB' | 'LR' = 'TB',
): SkillFlowGraphNode[] {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({
    rankdir: direction,
    ranksep: 72,
    nodesep: 48,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    graph.setNode(node.id, { width: 220, height: 96 });
  });

  edges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target);
  });

  dagre.layout(graph);

  return nodes.map((node) => {
    const next = graph.node(node.id);
    return {
      ...node,
      position: { x: next.x - 110, y: next.y - 48 },
    };
  });
}
