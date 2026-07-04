import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConnectionProfilesPage } from './ConnectionProfilesPage';
import { renderWithQueryClient } from '@/shared/test/render';

describe('ConnectionProfilesPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders fetched profile rows', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          msg: 'ok',
          data: {
            items: [
              {
                profileKey: 'openai.primary',
                displayName: 'OpenAI Primary',
                provider: 'openai',
                baseUrl: 'https://api.openai.com/v1',
                webSocketBaseUrl: null,
                apiVersion: null,
                region: null,
                extraJson: '{}',
                isEnabled: true,
              },
            ],
            page: 1,
            pageSize: 10,
            totalCount: 1,
          },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );

    renderWithQueryClient(<ConnectionProfilesPage />);

    expect(await screen.findByText('OpenAI Primary')).toBeInTheDocument();
    expect(screen.getByText('openai.primary')).toBeInTheDocument();
  });
});
