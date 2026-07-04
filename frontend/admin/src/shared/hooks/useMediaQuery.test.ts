import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMediaQuery } from './useMediaQuery';

function makeMql(matches: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  return {
    matches,
    addEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => listeners.push(fn),
    removeEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      const i = listeners.indexOf(fn);
      if (i !== -1) listeners.splice(i, 1);
    },
    _fire(nextMatches: boolean) {
      listeners.forEach((fn) => fn({ matches: nextMatches } as MediaQueryListEvent));
    },
  };
}

let mql: ReturnType<typeof makeMql>;

beforeEach(() => {
  mql = makeMql(false);
  vi.spyOn(window, 'matchMedia').mockReturnValue(mql as unknown as MediaQueryList);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useMediaQuery', () => {
  it('returns the initial match state', () => {
    mql = makeMql(true);
    vi.spyOn(window, 'matchMedia').mockReturnValue(mql as unknown as MediaQueryList);
    const { result } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    expect(result.current).toBe(true);
  });

  it('updates when the media query fires a change event', () => {
    const { result } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    expect(result.current).toBe(false);
    act(() => { mql._fire(true); });
    expect(result.current).toBe(true);
  });

  it('removes the event listener on unmount', () => {
    const removespy = vi.spyOn(mql, 'removeEventListener');
    const { unmount } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    unmount();
    expect(removespy).toHaveBeenCalledOnce();
  });
});
