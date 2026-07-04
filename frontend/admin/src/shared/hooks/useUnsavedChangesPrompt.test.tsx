import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';

const blockerState = {
  state: 'unblocked' as 'unblocked' | 'blocked' | 'proceeding',
  proceed: vi.fn(),
  reset: vi.fn(),
};

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useBlocker: vi.fn(() => blockerState),
  };
});

import { useUnsavedChangesPrompt } from './useUnsavedChangesPrompt';

function Harness({ when }: { when: boolean }) {
  useUnsavedChangesPrompt(when, '你有未保存的术语绑定变更，确定离开吗？');
  return null;
}

describe('useUnsavedChangesPrompt', () => {
  afterEach(() => {
    blockerState.state = 'unblocked';
    blockerState.proceed.mockReset();
    blockerState.reset.mockReset();
    vi.restoreAllMocks();
  });

  it('shows confirm and resets navigation when the user cancels', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    blockerState.state = 'blocked';

    render(<Harness when />);

    expect(window.confirm).toHaveBeenCalledWith('你有未保存的术语绑定变更，确定离开吗？');
    expect(blockerState.reset).toHaveBeenCalled();
    expect(blockerState.proceed).not.toHaveBeenCalled();
  });

  it('proceeds when the user accepts the leave warning', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    blockerState.state = 'blocked';

    render(<Harness when />);

    expect(blockerState.proceed).toHaveBeenCalled();
  });
});
