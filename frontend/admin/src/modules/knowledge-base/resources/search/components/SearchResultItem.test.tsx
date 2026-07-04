import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SearchResultItem } from './SearchResultItem';

describe('SearchResultItem', () => {
  it('labels the headline score as ranking when mixed recall final score differs from local composite score', () => {
    render(
      <SearchResultItem
        query="azure"
        searchMode="hybrid"
        result={{
          segmentId: '1',
          documentId: '101',
          content: 'Azure and local hybrid result',
          score: 2.36,
          vectorScore: 1,
          fulltextScore: 1,
          documentName: 'test.txt',
          metadataJson: JSON.stringify({
            recall_sources: ['local', 'azure_chunk_push'],
            local_search_score: 1.08,
            azure_search_score: 2.36,
          }),
        }}
      />,
    );

    expect(screen.getByText('排序 2.36')).toBeInTheDocument();
    expect(screen.getByText('综合分')).toBeInTheDocument();
    expect(screen.getByText('1.08')).toBeInTheDocument();
    expect(screen.getAllByText('Azure').length).toBeGreaterThan(0);
  });
});
