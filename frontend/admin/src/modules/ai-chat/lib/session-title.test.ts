import { afterEach, describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { buildSessionTitle } from './session-title';

describe('buildSessionTitle', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('normalizes whitespace and truncates long previews', () => {
    expect(buildSessionTitle('Planner', '  build   an   onboarding   checklist  for launch ')).toBe(
      'build an onboardin...',
    );
  });

  it('falls back to model name plus locale-aware time when message is empty', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-14T08:09:10Z'));

    await switchTestLanguage('en-US');
    expect(buildSessionTitle('Planner', '')).toBe(`Planner - ${new Date().toLocaleTimeString('en-US')}`);

    await switchTestLanguage('zh-CN');
    expect(buildSessionTitle('Planner', '')).toBe(`Planner - ${new Date().toLocaleTimeString('zh-CN')}`);
  });
});
