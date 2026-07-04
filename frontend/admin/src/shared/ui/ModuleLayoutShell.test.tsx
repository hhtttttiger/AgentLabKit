import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ModuleLayoutShell } from './ModuleLayoutShell';

const SECTIONS = [
  { key: 'overview', label: '概览', path: '/' },
  { key: 'list', label: '列表', path: '/list' },
];

describe('ModuleLayoutShell', () => {
  it('renders eyebrow, title, and section tabs', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={
              <ModuleLayoutShell eyebrow="AI 模型中心" title="模型管理" sections={SECTIONS} />
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('AI 模型中心')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '模型管理' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '概览' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '列表' })).toBeInTheDocument();
  });

  it('renders children when provided', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={
              <ModuleLayoutShell eyebrow="AI 模型中心" title="模型管理" sections={SECTIONS}>
                <div>page content</div>
              </ModuleLayoutShell>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('page content')).toBeInTheDocument();
  });
});
