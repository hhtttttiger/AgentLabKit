import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Button } from './Button';
import { TextField, SelectField } from './FormFields';
import { FilterToolbar } from './FilterToolbar';

describe('FilterToolbar typography', () => {
  it('applies toolbar-specific text sizing to controls', () => {
    render(
      <FilterToolbar actions={<Button>新建模型</Button>}>
        <TextField label="能力" placeholder="搜索能力" />
        <SelectField label="启用状态" defaultValue="all">
          <option value="all">全部状态</option>
        </SelectField>
      </FilterToolbar>,
    );

    const toolbar = screen
      .getByRole('button', { name: '新建模型' })
      .closest('div[class*="animate-box-enter"]');

    expect(toolbar).toHaveClass('[&_input]:text-xs');
    expect(toolbar).toHaveClass('[&_input]:placeholder:text-xs');
    expect(toolbar).toHaveClass('[&_select]:text-xs');
    expect(toolbar).toHaveClass('[&_button]:text-[11px]');
  });
});
