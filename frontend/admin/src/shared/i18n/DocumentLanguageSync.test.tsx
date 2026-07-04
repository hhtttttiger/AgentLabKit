import { render, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import i18n from './index';
import { DocumentLanguageSync } from './DocumentLanguageSync';

describe('DocumentLanguageSync', () => {
  it('syncs html lang and data-locale with i18n language changes', async () => {
    render(<DocumentLanguageSync />);

    await i18n.changeLanguage('en-US');
    await waitFor(() => {
      expect(document.documentElement.lang).toBe('en-US');
      expect(document.documentElement.dataset.locale).toBe('en-US');
    });
  });
});
