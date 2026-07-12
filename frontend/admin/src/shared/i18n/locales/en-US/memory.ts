// Auto-generated — do not edit manually
export const memory = {
  label: 'Memory',
  summary: 'Manage AI Agent memory storage.',
  eyebrow: 'Memory',
  title: 'Memory',
  sections: {
    memories: 'Memory List'
  },
  list: {
    title: 'Memory List',
    description: 'Manage Agent long-term memory and context.',
    searchPlaceholder: 'Search memory...',
    emptyTitle: 'No memory data',
    emptyDescription: 'Memory data will appear here once the Agent starts interacting.',
    filterAll: 'All',
    typeLabels: {
      episodic: 'Episodic',
      semantic: 'Semantic',
      procedural: 'Procedural'
    },
    accessCount: '{{count}} accesses',
    relevance: 'Relevance {{score}}',
    deactivate: 'Deactivate',
    consolidate: 'Consolidate',
    prevPage: 'Previous',
    nextPage: 'Next',
    pageInfo: 'Page {{page}} / {{total}}',
    metrics: {
      totalActive: 'Total',
      episodic: 'Episodic',
      semantic: 'Semantic',
      procedural: 'Procedural'
    },
    loadError: 'Failed to load memories. Please refresh.',
    filterLabel: 'Filter memories by type'
  }
} as const;
