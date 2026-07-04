import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelSelector } from './ModelSelector';
import type { ModelOption } from '../lib/contracts';

const modelOptions: ModelOption[] = [
  {
    id: 'card.primary',
    name: 'Primary Card',
    type: 'model',
  },
];

describe('ModelSelector', () => {
  it('hides the agent toggle when no agent options are available', () => {
    render(
      <ModelSelector
        agentOptions={[]}
        modelOptions={modelOptions}
        selectedModel={modelOptions[0]}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: 'Agent' })).not.toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('selects the first agent option when switching modes', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const agentOptions: ModelOption[] = [
      {
        id: 'agent.chat',
        name: 'Chat Agent',
        type: 'agent',
      },
    ];

    render(
      <ModelSelector
        agentOptions={agentOptions}
        modelOptions={modelOptions}
        selectedModel={modelOptions[0]}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Agent' }));

    expect(onSelect).toHaveBeenCalledWith(agentOptions[0]);
  });

  it('exposes translated compact mode labels', async () => {
    await switchTestLanguage('en-US');

    const agentOptions: ModelOption[] = [
      {
        id: 'agent.chat',
        name: 'Chat Agent',
        type: 'agent',
      },
    ];

    render(
      <ModelSelector
        agentOptions={agentOptions}
        modelOptions={modelOptions}
        selectedModel={agentOptions[0]}
        onSelect={vi.fn()}
        variant="compact"
      />,
    );

    expect(screen.getByRole('button', { name: 'Agent' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Model' })).toHaveAttribute('aria-pressed', 'false');
  });
});
