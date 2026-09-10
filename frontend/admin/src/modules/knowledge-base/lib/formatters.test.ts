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
    // Labels are locale keys under knowledgeBase:documentDetail.stage.*;
    // surfaces translate them at render time.
    expect(getPipelineSteps('Indexing')).toEqual([
      { stage: 'Loading', label: 'documentDetail.stage.Loading', status: 'done' },
      { stage: 'Splitting', label: 'documentDetail.stage.Splitting', status: 'done' },
      { stage: 'Indexing', label: 'documentDetail.stage.Indexing', status: 'active' },
      { stage: 'Completed', label: 'documentDetail.stage.Completed', status: 'pending' },
    ]);
  });
});
