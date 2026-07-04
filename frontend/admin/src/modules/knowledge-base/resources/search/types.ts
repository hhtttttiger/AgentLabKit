export type SearchMode = 'hybrid' | 'vector' | 'fulltext';

export type SearchFormState = {
  query: string;
  topK: number;
  searchMode: SearchMode;
};

export const defaultSearchForm: SearchFormState = {
  query: '',
  topK: 10,
  searchMode: 'hybrid',
};
