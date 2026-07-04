import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelMonitoringOverviewPage } from './ModelMonitoringOverviewPage';

vi.mock('@/modules/model-management/options/hooks', () => ({
  useModelOptions: () => ({
    data: [],
    isLoading: false,
  }),
}));

vi.mock('../resources/usage/hooks', () => ({
  useMonitoringOverview: () => ({
    data: null,
    isLoading: false,
  }),
}));

describe('ModelMonitoringOverviewPage', () => {
  it('renders English metric labels and empty state copy', async () => {
    await switchTestLanguage('en-US');

    render(<ModelMonitoringOverviewPage />);

    expect(screen.getByText('Total requests')).toBeInTheDocument();
    expect(screen.getByText('Total tokens')).toBeInTheDocument();
    expect(screen.getByText('Average latency')).toBeInTheDocument();
    expect(screen.getByText('Total errors')).toBeInTheDocument();
    expect(screen.getByText('No monitoring data')).toBeInTheDocument();
    expect(screen.getByText('Monitoring data will appear here after models start receiving traffic.')).toBeInTheDocument();
  });
});
