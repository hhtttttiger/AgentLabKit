import type { MouseEvent } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './skill-flow-canvas.css';
import type { SkillFlowState, SkillFlowTransition } from '../lib/types';
import { skillFlowNodeTypes } from './SkillFlowNodes';

type SkillFlowCanvasProps = {
  nodes: Array<Node<SkillFlowState>>;
  edges: Array<Edge<SkillFlowTransition>>;
  onNodesChange?: OnNodesChange<Node<SkillFlowState>>;
  onEdgesChange?: OnEdgesChange<Edge<SkillFlowTransition>>;
  onSelectState: (id: string | null) => void;
  onSelectTransition: (id: string | null) => void;
};

export function SkillFlowCanvas(props: SkillFlowCanvasProps) {
  return (
    <div className="skill-flow-canvas h-full min-h-[420px] rounded-[2px] border border-border bg-surface p-3">
      <ReactFlowProvider>
        <ReactFlow
          fitView
          fitViewOptions={{ padding: 0.18, maxZoom: 1.1 }}
          nodes={props.nodes}
          edges={props.edges}
          onNodesChange={props.onNodesChange}
          onEdgesChange={props.onEdgesChange}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          selectNodesOnDrag={false}
          defaultEdgeOptions={{
            type: 'smoothstep',
            animated: false,
            style: {
              stroke: 'rgb(var(--color-border-strong))',
              strokeWidth: 1.5,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 18,
              height: 18,
              color: 'rgb(var(--color-border-strong))',
            },
          }}
          onNodeClick={(_event: MouseEvent, node: Node<SkillFlowState>) => {
            props.onSelectState(node.id);
          }}
          onEdgeClick={(_event: MouseEvent, edge: Edge<SkillFlowTransition>) => {
            props.onSelectTransition(edge.id);
          }}
          onPaneClick={() => {
            props.onSelectState(null);
            props.onSelectTransition(null);
          }}
          nodeTypes={skillFlowNodeTypes}
          className="rounded-[2px] bg-transparent"
        >
          <Controls showInteractive={false} position="top-right" />
          <Background gap={18} size={1} color="rgb(var(--color-border-strong) / 0.35)" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
