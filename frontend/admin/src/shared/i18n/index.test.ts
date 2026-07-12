import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ADMIN_LOCALE_STORAGE_KEY } from './config';
import { createStorageMock } from '@/shared/test/storage';

describe('admin i18n initialization', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createStorageMock());
    localStorage.clear();
    vi.resetModules();
  });

  it('loads the saved locale and resolves translated common copy', async () => {
    window.localStorage.setItem(ADMIN_LOCALE_STORAGE_KEY, 'en-US');
    const { default: i18n } = await import('./index');

    expect(i18n.t('userMenu.ariaLabel')).toBe('User menu');
    expect(i18n.t('preferences.language.label')).toBe('Display language');
    expect(i18n.resolvedLanguage ?? i18n.language).toBe('en-US');
  });

  it('falls back to zh-CN when the saved locale is unsupported', async () => {
    window.localStorage.setItem(ADMIN_LOCALE_STORAGE_KEY, 'fr-FR');
    const { default: i18n } = await import('./index');

    expect(i18n.t('userMenu.ariaLabel')).toBe('用户菜单');
    expect(i18n.resolvedLanguage ?? i18n.language).toBe('zh-CN');
  });

  it('does not persist navigator-detected english into localStorage when storage is empty', async () => {
    vi.stubGlobal('navigator', {
      language: 'en-US',
      languages: ['en-US'],
    } as unknown as Navigator);

    const { default: i18n } = await import('./index');

    expect(i18n.resolvedLanguage ?? i18n.language).toBe('en-US');
    expect(i18n.services.languageDetector?.options.caches ?? []).not.toContain('localStorage');
    expect(window.localStorage.getItem(ADMIN_LOCALE_STORAGE_KEY)).toBeNull();
  });

  it('contains rollout navigation and module copy in both locales', async () => {
    window.localStorage.setItem(ADMIN_LOCALE_STORAGE_KEY, 'en-US');
    const { adminI18nResources } = await import('./resources');

    expect(adminI18nResources['zh-CN'].common.nav.knowledgeBase).toBe('知识库');
    expect(adminI18nResources['en-US'].common.nav.knowledgeBase).toBe('Knowledge base');
    expect(adminI18nResources['zh-CN'].knowledgeBase.list.title).toBe('知识库');
    expect(adminI18nResources['en-US'].knowledgeBase.list.title).toBe('Knowledge base');
  });

  it('falls back to zh-CN when ja-JP locale is saved but removed', async () => {
    window.localStorage.setItem(ADMIN_LOCALE_STORAGE_KEY, 'ja-JP');
    const { default: i18n } = await import('./index');

    expect(i18n.t('userMenu.ariaLabel')).toBe('用户菜单');
    expect(i18n.resolvedLanguage ?? i18n.language).toBe('zh-CN');
  });
});
