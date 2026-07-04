import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KbCreateDrawer } from './KbCreateDrawer';

describe('KbCreateDrawer', () => {
  it('disables provider selection in edit mode and shows immutable hint', () => {
    render(
      <KbCreateDrawer
        open
        mode="edit"
        initialValue={{
          id: 'kb-1',
          name: 'Azure KB',
          description: 'desc',
          sourceType: 'Local',
          documentCount: 3,
          status: 'Active',
          settingsJson: '{"version":1,"provider":"azure","azure":{"profileId":"azure-search-default"}}',
          createdAtUtc: '2026-04-24T00:00:00Z',
        }}
        loading={false}
        onSubmit={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('Provider')).toBeDisabled();
    expect(screen.getByText('创建后不可修改，避免索引损坏。')).toBeInTheDocument();
  });
});
