import { describe, expect, it } from 'vitest';
import { formatFileSize, getPipelineSteps } from './formatters';

describe('knowledge base formatters', () => {
  it('formats file sizes with stable units', () => {
    expect(formatFileSize(undefined)).toBe('-');
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(2 * 1024 * 1024)).toBe('2.0 MB');
  });

  it('maps intermediate pipeline stages to done, active, and pending steps', () => {
    expect(getPipelineSteps('Indexing')).toEqual([
      { stage: 'Loading', label: '加载文件', status: 'done' },
      { stage: 'Splitting', label: '文本切分', status: 'done' },
      { stage: 'Indexing', label: '构建索引', status: 'active' },
      { stage: 'Completed', label: '已完成', status: 'pending' },
    ]);
  });
});
