import type { PagedResult } from '@/shared/types/paging';

export type GlossaryCategoryView = {
  id: string;
  name: string;
  description?: string | null;
  createdAtUtc: string;
  updatedAtUtc?: string | null;
};

export type GlossaryTermView = {
  id: string;
  categoryId: string;
  term: string;
  synonyms: string[];
  createdAtUtc: string;
  updatedAtUtc?: string | null;
};

export type GlossaryImportResult = {
  importedCount: number;
  errors: string[];
};

export type GlossaryCategoryListQuery = {
  page?: number;
  pageSize?: number;
  search?: string;
};

export type GlossaryTermListQuery = {
  categoryId?: string;
  page?: number;
  pageSize?: number;
  search?: string;
};

export type GlossaryCategoryCreateRequest = {
  name: string;
  description?: string;
};

export type GlossaryCategoryUpdateRequest = {
  name?: string;
  description?: string;
};

export type GlossaryTermCreateRequest = {
  categoryId: string;
  term: string;
  synonyms: string[];
};

export type GlossaryTermUpdateRequest = {
  categoryId?: string;
  term?: string;
  synonyms?: string[];
};

export type GlossaryCategoryPage = PagedResult<GlossaryCategoryView>;
export type GlossaryTermPage = PagedResult<GlossaryTermView>;
