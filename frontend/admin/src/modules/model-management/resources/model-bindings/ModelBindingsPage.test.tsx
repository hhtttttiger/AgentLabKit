import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelBindingsPage } from './ModelBindingsPage';

describe('ModelBindingsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders translated filters and actions', async () => {
    await switchTestLanguage('en-US');

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes('/api/llm-catalog/model-bindings')) {
        return new Response(
          JSON.stringify({
            success: true,
            msg: 'ok',
            data: {
              items: [
                {
                  bindingKey: 'binding.default',
                  displayName: 'Default binding',
                  capability: 'Text',
                  modelKey: 'card.text',
                  isEnabled: true,
                  metadataJson: '{}',
                },
              ],
              page: 1,
              pageSize: 10,
              totalCount: 1,
            },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    renderWithQueryClient(<ModelBindingsPage />);

    expect(await screen.findByRole('button', { name: 'New binding' })).toBeInTheDocument();
    expect(screen.getByLabelText('Capability')).toBeInTheDocument();
  });
});
