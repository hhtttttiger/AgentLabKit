import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelBindingDrawer } from './ModelBindingDrawer';

describe('ModelBindingDrawer', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads selectable model card options', async () => {
    await switchTestLanguage('en-US');

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes('/api/llm-catalog/options/models')) {
        return new Response(
          JSON.stringify({
            success: true,
            msg: 'ok',
            data: [{ modelKey: 'card.voice', displayName: '语音助手', isEnabled: true }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    renderWithQueryClient(
      <ModelBindingDrawer
        open
        mode="create"
        initialValue={null}
        loading={false}
        error={null}
        onClose={() => {}}
        onSubmit={async () => {}}
      />,
    );

    expect(screen.getByText('New binding')).toBeInTheDocument();
    expect(screen.getByLabelText('Binding key')).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: '语音助手 (card.voice)' })).toBeInTheDocument();
  });
});
