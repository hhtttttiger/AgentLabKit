// Auto-generated — do not edit manually
export const knowledgeBase = {
  label: 'Knowledge base',
  summary: 'Manage knowledge bases, upload documents, and run retrieval tests.',
  title: 'Knowledge base',
  list: {
    title: 'Knowledge base',
    description: 'Manage knowledge bases, upload documents, and test search results.',
    create: 'Create knowledge base',
    searchLabel: 'Search',
    searchPlaceholder: 'Knowledge base name...',
    statusLabel: 'Status',
    statuses: {
      all: 'All',
      active: 'Active',
      processing: 'Processing',
      disabled: 'Disabled'
    },
    emptyTitle: 'No knowledge bases',
    emptyDescription: 'Click "Create knowledge base" to get started.',
    deleteTitle: 'Delete knowledge base',
    deleteDescription: 'Are you sure you want to delete "{{name}}"?'
  },
  detail: {
    eyebrow: 'Knowledge base',
    fallbackTitle: 'Knowledge base',
    backToList: 'Back to knowledge base list',
    updateSuccess: 'Knowledge base updated',
    updateFailed: 'Failed to update knowledge base',
    sections: {
      overview: 'Overview',
      documents: 'Documents',
      glossary: 'Glossary bindings',
      search: 'Search test'
    },
    glossaryBindingDescription: 'Select glossary categories to participate in term matching for this knowledge base. Saving will overwrite the existing bindings.',
    glossarySave: 'Save bindings',
    glossarySaving: 'Saving...',
    glossaryDescriptionFallback: 'No description provided',
    glossaryRefreshFailed: 'Failed to refresh latest state; showing cached results.',
    glossaryEmptyTitle: 'No glossary categories',
    glossaryEmptyDescription: 'Create categories in the Glossary module first, then come back to bind them to this knowledge base.',
    segmentEmptyTitle: 'No segments',
    folderEmptyTitle: 'No folders'
  }
} as const;
