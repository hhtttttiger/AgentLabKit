import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelInstanceDrawer } from './ModelInstanceDrawer';

describe('ModelInstanceDrawer', () => {
  function mockModelOptions() {
    return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes('/api/llm-catalog/options/models')) {
        return new Response(
          JSON.stringify({
            success: true,
            msg: 'ok',
            data: [{ modelKey: 'card.text', displayName: '文本能力', isEnabled: true }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
  }

  function submitButton() {
    return screen.getAllByRole('button').at(-1)!;
  }

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads selectable card options and hides provider model selection', async () => {
    mockModelOptions();

    renderWithQueryClient(
      <ModelInstanceDrawer
        open
        mode="create"
        initialValue={null}
        loading={false}
        error={null}
        onClose={() => {}}
        onSubmit={async () => {}}
      />,
    );

    expect(await screen.findByRole('option', { name: '文本能力 (card.text)' })).toBeInTheDocument();

    const [cardSelect] = screen.getAllByRole('combobox');
    fireEvent.change(cardSelect, { target: { value: 'card.text' } });

    expect(screen.queryByRole('combobox', { name: '模型名称' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('部署名称')).toBeInTheDocument();
  });

  it('submits runtime-only instance fields with required API key', async () => {
    const onSubmit = vi.fn(async () => {});

    mockModelOptions();

    renderWithQueryClient(
      <ModelInstanceDrawer
        open
        mode="create"
        initialValue={null}
        loading={false}
        error={null}
        onClose={() => {}}
        onSubmit={onSubmit}
      />,
    );

    expect(await screen.findByRole('option', { name: '文本能力 (card.text)' })).toBeInTheDocument();

    const [cardSelect] = screen.getAllByRole('combobox');
    fireEvent.change(cardSelect, { target: { value: 'card.text' } });
    fireEvent.change(screen.getByLabelText('实例标识'), { target: { value: 'instance.text.primary' } });
    fireEvent.change(screen.getByLabelText('部署名称'), { target: { value: 'deploy-alpha' } });
    fireEvent.change(screen.getByLabelText(/API/i), { target: { value: 'sk-test-key-123' } });

    fireEvent.click(submitButton());

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        modelKey: 'card.text',
        model: expect.objectContaining({
          instanceKey: 'instance.text.primary',
          providerDeploymentName: 'deploy-alpha',
          apiKey: 'sk-test-key-123',
        }),
      });
    });
  });

  it('shows API key field in edit mode and allows keeping the existing key', async () => {
    const onSubmit = vi.fn(async () => {});
    mockModelOptions();

    renderWithQueryClient(
      <ModelInstanceDrawer
        open
        mode="edit"
        initialValue={{
          modelKey: 'card.text',
          instanceKey: 'instance.text.primary',
          type: 'Text',
          modelName: 'gpt-4.1-mini',
          providerDeploymentName: 'deploy-alpha',
          region: null,
          priority: 1,
          weight: 100,
          defaultTimeoutMs: 30000,
          extraJson: {},
          isEnabled: true,
          isHealthy: true,
        }}
        modelKeyPreset="card.text"
        loading={false}
        error={null}
        onClose={() => {}}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByLabelText(/API/i)).toBeInTheDocument();
    fireEvent.click(submitButton());

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        modelKey: 'card.text',
        model: expect.objectContaining({
          instanceKey: 'instance.text.primary',
          apiKey: null,
        }),
      });
    });
  });

  it('shows validation error when API key is empty', async () => {
    await switchTestLanguage('en-US');

    mockModelOptions();

    renderWithQueryClient(
      <ModelInstanceDrawer
        open
        mode="create"
        initialValue={null}
        loading={false}
        error={null}
        onClose={() => {}}
        onSubmit={async () => {}}
      />,
    );

    expect(await screen.findByRole('option', { name: '文本能力 (card.text)' })).toBeInTheDocument();

    const [cardSelect] = screen.getAllByRole('combobox');
    fireEvent.change(cardSelect, { target: { value: 'card.text' } });
    fireEvent.change(screen.getByLabelText('Instance key'), { target: { value: 'instance.text.primary' } });

    fireEvent.click(submitButton());

    await waitFor(() => {
      expect(screen.getByText('Please enter an API key.')).toBeInTheDocument();
    });
  });
});
