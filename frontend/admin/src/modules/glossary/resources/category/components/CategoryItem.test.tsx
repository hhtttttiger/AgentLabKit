import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { CategoryItem } from './CategoryItem';

describe('CategoryItem', () => {
  it('shows translated fallback description and actions', async () => {
    await switchTestLanguage('en-US');

    render(
      <CategoryItem
        category={{
          id: 'cat-1',
          name: 'RAG',
          description: '',
          createdAtUtc: '2026-04-27T00:00:00Z',
          updatedAtUtc: null,
        }}
        active={false}
        onSelect={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText('No category description')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });
});
