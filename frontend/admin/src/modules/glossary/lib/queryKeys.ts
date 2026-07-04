export const glossaryQueryKeys = {
  all: () => ['glossary'] as const,
  categories: (filters?: unknown) => ['glossary', 'categories', filters] as const,
  terms: (filters?: unknown) => ['glossary', 'terms', filters] as const,
  term: (termId: string | undefined) => ['glossary', 'term', termId] as const,
  kbBindings: (kbId: string | undefined) => ['glossary', 'kb-bindings', kbId] as const,
};
