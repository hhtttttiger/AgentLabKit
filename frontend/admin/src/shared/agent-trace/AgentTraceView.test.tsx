import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AgentTraceView } from './AgentTraceView';
import type { AgentExecutionTrace } from './contracts';

const trace: AgentExecutionTrace = {
  runId: 'run-1',
  sessionId: 'session-1',
  traceId: 'trace-1',
  agentKey: 'weather-agent',
  agentVersion: 2,
  status: 'success',
  action: 'weather_lookup',
  appliedSkills: [],
  toolEvents: [
    {
      toolName: 'weather_query',
      displayName: 'Weather Query',
      status: 'success',
      arguments: {
        city: 'Guangzhou',
        units: 'metric',
      },
      outputText: 'Sunny with a high of 31C\nHumidity 72%',
      tags: ['external'],
    },
  ],
  steps: [],
};

describe('AgentTraceView', () => {
  it('renders readable Chinese copy for the trace header and empty state', () => {
    render(<AgentTraceView trace={null} />);

    expect(screen.getByText('执行轨迹')).toBeInTheDocument();
    expect(screen.getByText('上下文、skills、工具与回复过程会按时间顺序显示。')).toBeInTheDocument();
    expect(screen.getByText('暂无可视化轨迹')).toBeInTheDocument();
    expect(screen.getByText('发送一条 Agent 消息后，这里会展示运行过程与结果。')).toBeInTheDocument();
  });

  it('renders readable code blocks with vertical scrolling for tool payloads', () => {
    render(<AgentTraceView trace={trace} />);

    const argumentsBlock = screen.getByText(/"city": "Guangzhou"/).closest('pre');
    const outputBlock = screen.getByText(/Sunny with a high of 31C/).closest('pre');

    expect(argumentsBlock).toHaveClass('overflow-auto');
    expect(argumentsBlock).toHaveClass('bg-[#0f1f33]');
    expect(argumentsBlock).toHaveClass('text-[#e8f1ff]');
    expect(outputBlock).toHaveClass('overflow-auto');
    expect(outputBlock).toHaveClass('max-h-[220px]');
  });

  it('expands tool arguments and output on demand', () => {
    render(<AgentTraceView trace={trace} />);

    const toggle = screen.getByRole('button', { name: /展开入参与输出/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveTextContent('收起');
  });
});
