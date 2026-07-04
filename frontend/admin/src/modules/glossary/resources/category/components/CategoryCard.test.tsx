import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { CategoryCard } from './CategoryCard';

describe('CategoryCard', () => {
  it('shows translated menu actions', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');

    render(
      <CategoryCard
        category={{
          id: 'cat-1',
          name: 'RAG',
          description: '',
          createdAtUtc: '2026-04-27T00:00:00Z',
          updatedAtUtc: null,
        }}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });
});
