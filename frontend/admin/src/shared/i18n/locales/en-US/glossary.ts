// Auto-generated — do not edit manually
export const glossary = {
  label: 'Glossary',
  summary: 'Manage glossary categories and terms, then bind them to knowledge bases.',
  eyebrow: 'Knowledge augmentation',
  title: 'Glossary',
  sections: {
    list: 'Glossary management'
  },
  list: {
    title: 'Glossary',
    description: 'Manage glossary categories and terms, then bind them to knowledge bases.',
    newCategory: 'New category',
    searchLabel: 'Search',
    searchPlaceholder: 'Category name...',
    emptyTitle: 'No glossary categories',
    emptyDescription: 'Click "New category" to get started.',
    deleteTitle: 'Delete category',
    deleteDescription: 'Are you sure you want to delete category "{{name}}"?',
    confirmDelete: 'Delete category'
  },
  categoryForm: {
    titleCreate: 'New category',
    titleEdit: 'Edit category',
    description: 'Categories group glossary terms and serve as the smallest knowledge base binding unit.',
    fields: {
      name: 'Category name',
      namePlaceholder: 'For example: RAG',
      description: 'Description',
      descriptionPlaceholder: 'Optional. Describe when this category should be used.'
    },
    actions: {
      cancel: 'Cancel',
      submitting: 'Saving...',
      create: 'Create category',
      save: 'Save'
    },
    validation: {
      nameRequired: 'Please enter a category name.'
    }
  },
  category: {
    fallbackTitle: 'Glossary category',
    eyebrow: 'Glossary',
    backToList: 'Back to glossary',
    sections: {
      terms: 'Terms'
    }
  },
  categoryCard: {
    menuLabel: 'Category actions',
    actions: {
      edit: 'Edit',
      delete: 'Delete'
    }
  },
  categoryItem: {
    descriptionFallback: 'No category description',
    actions: {
      edit: 'Edit',
      delete: 'Delete'
    }
  },
  termsTab: {
    columns: {
      term: 'Term',
      synonyms: 'Synonyms',
      createdAt: 'Created at',
      actions: 'Actions'
    },
    rowActions: {
      edit: 'Edit',
      delete: 'Delete'
    },
    toolbar: {
      import: 'Import terms',
      create: 'New term',
      searchLabel: 'Search',
      searchPlaceholder: 'Search terms or synonyms...'
    },
    emptyTitle: 'No terms',
    emptyDescription: 'There are no terms in this category yet. Add one manually or import a file.',
    emptyAction: 'Add term',
    deleteTitle: 'Delete term',
    deleteDescription: 'Are you sure you want to delete term "{{name}}"?',
    confirmDelete: 'Delete term'
  },
  termForm: {
    titleCreate: 'New term',
    titleEdit: 'Edit term',
    description: 'Terms and synonyms are used for glossary matching, imports, and knowledge base bindings.',
    fields: {
      category: 'Category',
      categoryPlaceholder: 'Please select a category',
      term: 'Term',
      termPlaceholder: 'For example: Embedding',
      synonyms: 'Synonyms',
      synonymsHint: 'Enter one synonym per line, or separate them with commas.',
      synonymsPlaceholder: 'For example: Vectorization'
    },
    actions: {
      cancel: 'Cancel',
      submitting: 'Saving...',
      create: 'Create term',
      save: 'Save'
    },
    validation: {
      categoryRequired: 'Please select a category.',
      termRequired: 'Please enter a term name.'
    }
  },
  termImport: {
    title: 'Import terms',
    description: 'Upload a CSV file to import terms and review row-level errors.',
    actions: {
      cancel: 'Cancel',
      importing: 'Importing...',
      submit: 'Import terms',
      downloadTemplate: 'Download import template'
    },
    upload: {
      replaceFile: 'Click to choose another file',
      selectFile: 'Click to upload a file',
      hint: 'Supports .csv and .xlsx files'
    },
    template: {
      prompt: 'Need a template?'
    },
    result: {
      importedCount: 'Imported {{count}} terms',
      noErrors: 'No row-level errors were returned.'
    },
    errorFallback: 'Import failed. Please try again later.'
  },
  termItem: {
    noSynonyms: 'No synonyms',
    actions: {
      edit: 'Edit',
      delete: 'Delete'
    }
  }
} as const;
