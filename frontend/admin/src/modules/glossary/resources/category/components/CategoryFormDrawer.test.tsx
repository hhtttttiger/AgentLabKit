import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { CategoryFormDrawer } from './CategoryFormDrawer';

describe('CategoryFormDrawer', () => {
  it('renders translated create copy and validation', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');

    render(
      <CategoryFormDrawer
        open
        mode="create"
        initialValue={null}
        loading={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByRole('heading', { name: 'New category' })).toBeInTheDocument();
    expect(screen.getByLabelText('Category name')).toBeInTheDocument();
    expect(screen.getByText('Please enter a category name.')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Category name'), 'RAG');
    expect(screen.queryByText('Please enter a category name.')).not.toBeInTheDocument();
  });
});
