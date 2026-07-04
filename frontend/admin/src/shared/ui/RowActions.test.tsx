import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RowActions } from './RowActions';

const actions = [
  { label: '管理 Prompt 与版本', onClick: vi.fn() },
  { label: '编辑定义', onClick: vi.fn() },
];

describe('RowActions', () => {
  it('renders a trigger button and no menu items initially', () => {
    render(<RowActions actions={actions} />);
    expect(screen.getByRole('button', { name: '更多操作' })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('opens the menu on trigger click', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    expect(screen.getByRole('menuitem', { name: '管理 Prompt 与版本' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '编辑定义' })).toBeInTheDocument();
  });

  it('calls the action onClick and closes the menu', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('menuitem', { name: '管理 Prompt 与版本' }));
    expect(actions[0].onClick).toHaveBeenCalledOnce();
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('closes the menu when Escape is pressed', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('closes the menu when clicking outside', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <RowActions actions={actions} />
        <button type="button">outside</button>
      </div>,
    );
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('button', { name: 'outside' }));
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('renders the menu outside clipping containers', async () => {
    const user = userEvent.setup();
    render(
      <div data-testid="clipper" className="overflow-hidden rounded-xl">
        <RowActions actions={actions} />
      </div>,
    );

    await user.click(screen.getByRole('button', { name: '更多操作' }));

    const clipper = screen.getByTestId('clipper');
    expect(screen.getByRole('menu')).toBeInTheDocument();
    expect(clipper).not.toContainElement(screen.getByRole('menu'));
  });
});
