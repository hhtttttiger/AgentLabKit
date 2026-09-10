import { screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { RunConfigFormModal } from './RunConfigFormModal';
import type { DatasetData } from '../../lib/contracts';

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: vi.fn() };
});

const dataset: DatasetData = {
  id: '1',
  name: 'Regression Set',
  description: null,
  tags: [],
  caseCount: 3,
  isActive: true,
  createdAtUtc: '2026-09-09T00:00:00Z',
  updatedAtUtc: '2026-09-09T00:00:00Z',
};

function renderModal(props: { datasets: DatasetData[] }) {
  return renderWithQueryClient(
    <RunConfigFormModal
      open
      datasets={props.datasets}
      loading={false}
      error={null}
      onClose={vi.fn()}
      onSubmit={vi.fn()}
    />,
  );
}

describe('RunConfigFormModal', () => {
  it('explains the dataset prerequisite instead of showing empty selects', async () => {
    renderModal({ datasets: [] });

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('暂无数据集。可先在运行详情页选择"添加到数据集"，或手动创建数据集，然后再开始评估。')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: '打开数据集' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: '运行评估' })).toBeDisabled();
  });

  it('renders the dataset selector with case counts when datasets exist', async () => {
    renderModal({ datasets: [dataset] });

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByText('暂无数据集。可先在运行详情页选择"添加到数据集"，或手动创建数据集，然后再开始评估。')).not.toBeInTheDocument();
    expect(within(dialog).getByText('Regression Set（3 条用例）')).toBeInTheDocument();
  });
});
