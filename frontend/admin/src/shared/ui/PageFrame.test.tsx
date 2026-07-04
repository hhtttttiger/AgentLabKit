import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PageFrame } from './PageFrame';
import { SectionPageFrame } from './SectionPageFrame';

describe('PageFrame', () => {
  it('uses a scrollable content area by default', () => {
    render(
      <PageFrame title="模型管理">
        <div>content</div>
      </PageFrame>,
    );

    expect(screen.getByText('content').parentElement).toHaveClass('overflow-y-auto');
  });

  it('can opt out of scrolling for flex layouts', () => {
    render(
      <PageFrame title="模型管理" scroll={false}>
        <div>content</div>
      </PageFrame>,
    );

    expect(screen.getByText('content').parentElement).toHaveClass('flex', 'flex-col');
    expect(screen.getByText('content').parentElement).not.toHaveClass('overflow-y-auto');
  });

  it('supports compact header spacing overrides', () => {
    render(
      <PageFrame
        title="模型管理"
        headerClassName="py-4"
        headerBodyClassName="min-w-0 flex-1 max-w-none"
        supportingClassName="mt-3"
        supporting={<div>summary</div>}
      >
        <div>content</div>
      </PageFrame>,
    );

    expect(screen.getByText('模型管理').closest('.mm-grid-pattern')).toHaveClass('py-4');
    expect(screen.getByText('模型管理').parentElement).toHaveClass('min-w-0', 'flex-1', 'max-w-none');
    expect(screen.getByText('summary').parentElement).toHaveClass('mt-3');
  });
});

describe('SectionPageFrame', () => {
  it('matches PageFrame scrolling defaults', () => {
    render(
      <SectionPageFrame sectionTitle="知识库" title="搜索测试">
        <div>details</div>
      </SectionPageFrame>,
    );

    expect(screen.getByText('details').parentElement).toHaveClass('overflow-y-auto');
  });
});
