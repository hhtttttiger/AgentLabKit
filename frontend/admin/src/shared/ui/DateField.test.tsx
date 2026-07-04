import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { DateField } from './FormFields';

describe('DateField', () => {
  it('renders the calendar overlay outside clipping containers', async () => {
    const user = userEvent.setup();
    await switchTestLanguage('en-US');

    render(
      <div data-testid="clipper" className="overflow-hidden rounded-xl">
        <DateField label="Start time" value="2024-01-15" onChange={vi.fn()} />
      </div>,
    );

    await user.click(screen.getByLabelText('Start time'));

    const clipper = screen.getByTestId('clipper');
    expect(screen.getByRole('dialog', { name: 'January 2024' })).toBeInTheDocument();
    expect(clipper).not.toContainElement(screen.getByRole('dialog', { name: 'January 2024' }));
  });
});
