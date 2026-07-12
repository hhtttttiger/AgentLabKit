import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { Pagination } from './Pagination';

describe('Pagination', () => {
  it('rerenders localized copy when the language changes', async () => {
    await switchTestLanguage('en-US');

    render(<Pagination page={2} pageSize={10} totalCount={45} onChange={vi.fn()} onPageSizeChange={vi.fn()} />);

    expect(screen.getByText((_, node) => node?.textContent === '45 total')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '10 / page' })).toBeInTheDocument();
    expect(screen.getByText('Go to')).toBeInTheDocument();
    expect(screen.getByText('page')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next page' })).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText((_, node) => node?.textContent === '共 45 条')).toBeInTheDocument();
    });
    expect(screen.getByRole('option', { name: '10 条/页' })).toBeInTheDocument();
    expect(screen.getByText('跳至')).toBeInTheDocument();
    expect(screen.getByText('页')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '上一页' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '下一页' })).toBeInTheDocument();
  });
});
