import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { VersionKnowledgeBaseBindingSection } from './VersionKnowledgeBaseBindingSection';

describe('VersionKnowledgeBaseBindingSection', () => {
  it('shows an info hint when KBs are configured but knowledge_search is not usable', () => {
    renderWithQueryClient(
      <VersionKnowledgeBaseBindingSection
        readOnly={false}
        hasUsableKnowledgeSearch={false}
        rows={[
          {
            id: 'binding-1',
            knowledgeBaseId: 'kb-1',
            knowledgeBaseName: 'Policies',
            knowledgeBaseStatus: 'Active',
            sortOrder: 10,
            isEnabled: true,
            config: {},
            createdAtUtc: '2026-04-30T00:00:00Z',
            updatedAtUtc: null,
          },
        ]}
        candidates={[]}
        validationErrors={{}}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        onUpdate={vi.fn()}
      />,
    );

    expect(screen.getByText(/当前 version 尚未绑定可用的 knowledge_search 工具/i)).toBeInTheDocument();
  });

  it('hides editing controls when readOnly is true', () => {
    renderWithQueryClient(
      <VersionKnowledgeBaseBindingSection
        readOnly
        hasUsableKnowledgeSearch
        rows={[]}
        candidates={[]}
        validationErrors={{}}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        onUpdate={vi.fn()}
      />,
    );

    expect(screen.getByText(/当前版本已发布/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '新增知识库绑定' })).not.toBeInTheDocument();
  });

  it('filters the add dialog down to unbound knowledge bases', async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();

    renderWithQueryClient(
      <VersionKnowledgeBaseBindingSection
        readOnly={false}
        hasUsableKnowledgeSearch
        rows={[]}
        candidates={[{ value: 'kb-2', label: 'FAQ', status: 'Active' }]}
        validationErrors={{}}
        onAdd={onAdd}
        onRemove={vi.fn()}
        onUpdate={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: '新增知识库绑定' }));

    expect(screen.getByRole('option', { name: 'FAQ' })).toBeInTheDocument();
  });
});
