import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelManagementLayout } from './ModelManagementLayout';

describe('ModelManagementLayout', () => {
  it('renders translated section labels in English', async () => {
    await switchTestLanguage('en-US');

    render(
      <MemoryRouter initialEntries={['/model-management/model-bindings']}>
        <ModelManagementLayout />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Model management' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Scenarios' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Provider connections' })).toBeInTheDocument();
  });
});
