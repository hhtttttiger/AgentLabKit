// Auto-generated — do not edit manually
export const knowledgeBase = {
  label: 'Knowledge base',
  summary: 'Manage knowledge bases, upload documents, and run retrieval tests.',
  title: 'Knowledge base',
  list: {
    title: 'Knowledge base',
    description: 'Give Agents access to your own documents and data, and verify what they retrieve.',
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
    emptyTitle: 'No knowledge bases yet',
    emptyDescription: 'Knowledge lets Agents retrieve information from your own documents and data. Create a knowledge base, add content, then bind it to an Agent.',
    deleteTitle: 'Delete knowledge base',
    deleteDescription: 'Are you sure you want to delete "{{name}}"?'
  },
  detail: {
    eyebrow: 'Knowledge base',
    fallbackTitle: 'Knowledge base',
    backToList: 'Back to knowledge base list',
    updateSuccess: 'Knowledge base updated',
    updateFailed: 'Failed to update knowledge base',
    useInAgent: 'Use in Agent',
    useInAgentTitle: 'Use this knowledge base in an Agent',
    useInAgentDescription: 'Choose an Agent. We will update its draft, or create one from the published version, and make knowledge retrieval usable.',
    useInAgentSelectLabel: 'Agent',
    useInAgentSelectPlaceholder: 'Select an Agent',
    useInAgentButton: 'Add knowledge',
    useInAgentSaving: 'Saving...',
    useInAgentSuccess: 'Knowledge base "{{name}}" was added to draft v{{versionNumber}}',
    useInAgentFailed: 'Failed to add knowledge base',
    useInAgentNoTarget: 'The selected Agent could not be found.',
    useInAgentNoVersion: 'This Agent has no editable draft or published version.',
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
