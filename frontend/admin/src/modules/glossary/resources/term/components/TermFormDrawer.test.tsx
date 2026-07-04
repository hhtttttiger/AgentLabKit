import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { TermFormDrawer } from './TermFormDrawer';

describe('TermFormDrawer', () => {
  it('shows a fixed translated category summary for the current pane instead of a category selector', async () => {
    await switchTestLanguage('en-US');
    render(
      <TermFormDrawer
        open
        mode="create"
        categories={[]}
        defaultCategoryId="cat-9"
        defaultCategoryName="知识增强"
        initialValue={null}
        loading={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('知识增强')).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Category' })).not.toBeInTheDocument();
  });

  it('keeps edit category context when the selected category is off the current page', async () => {
    await switchTestLanguage('en-US');
    render(
      <TermFormDrawer
        open
        mode="edit"
        categories={[]}
        defaultCategoryId="cat-9"
        defaultCategoryName="知识增强"
        initialValue={{
          id: 'term-1',
          categoryId: 'cat-9',
          term: 'Embedding',
          synonyms: [],
          createdAtUtc: '2026-04-27T00:00:00Z',
          updatedAtUtc: null,
        }}
        loading={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText('知识增强')).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Category' })).not.toBeInTheDocument();
  });

  it('submits against the selected category even when the paged category list is unavailable', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');
    const onSubmit = vi.fn();

    render(
      <TermFormDrawer
        open
        mode="create"
        categories={[]}
        defaultCategoryId="cat-9"
        defaultCategoryName="知识增强"
        initialValue={null}
        loading={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText('Term'), 'Embedding');
    await user.click(screen.getByRole('button', { name: 'Create term' }));

    expect(onSubmit).toHaveBeenCalledWith({
      categoryId: 'cat-9',
      term: 'Embedding',
      synonyms: [],
    });
  });
});
