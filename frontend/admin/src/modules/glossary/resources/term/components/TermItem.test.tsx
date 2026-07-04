import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { TermItem } from './TermItem';

describe('TermItem', () => {
  it('shows translated empty synonym and actions', async () => {
    await switchTestLanguage('en-US');

    render(
      <TermItem
        term={{
          id: 'term-1',
          categoryId: 'cat-1',
          term: 'Embedding',
          synonyms: [],
          createdAtUtc: '2026-04-27T00:00:00Z',
          updatedAtUtc: null,
        }}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText('No synonyms')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });
});
