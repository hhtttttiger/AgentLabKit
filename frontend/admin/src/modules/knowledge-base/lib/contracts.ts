// ── Enums ──

export type KbStatus = 'Active' | 'Processing' | 'Disabled' | 'Deleted';
export type DocumentSourceType = 'File' | 'QaPair';
export type IngestStatus = 'Pending' | 'Processing' | 'Completed' | 'Failed';
export type IndexType = 'Vector' | 'FullText' | 'Graph' | 'ChunkPushMirror';

// ── Knowledge Base ──

export type KbCreateRequest = {
  name: string;
  description?: string;
  settingsJson?: string;
};

export type KbUpdateRequest = {
  name?: string;
  description?: string;
  settingsJson?: string;
};

export type KbView = {
  id: string;
  name: string;
  description?: string;
  sourceType: string;
  documentCount: number;
  status: KbStatus;
  settingsJson?: string;
  metadataJson?: string;
  createdAtUtc: string;
  updatedAtUtc?: string;
};

// ── Folder ──

export type KbFolderView = {
  id: string;
  knowledgeBaseId: string;
  parentFolderId: string | null;
  name: string;
  sortOrder: number;
  createdAtUtc: string;
  updatedAtUtc?: string;
};

export type KbFolderCreateRequest = {
  name: string;
  parentFolderId?: string | null;
  sortOrder?: number;
};

export type KbFolderUpdateRequest = {
  name?: string;
  sortOrder?: number;
};

export type KbFolderMoveRequest = {
  targetParentFolderId: string | null;
};

export type KbDocumentMoveRequest = {
  targetFolderId: string | null;
};

// ── Document ──

export type KbQaCreateRequest = {
  question: string;
  answer: string;
  folderId?: string | null;
};

export type KbQaUpdateRequest = {
  question?: string;
  answer?: string;
};

export type KbDocumentView = {
  id: string;
  knowledgeBaseId: string;
  sourceType: DocumentSourceType;
  storedFileId?: string;
  fileName?: string;
  contentType?: string;
  fileSize?: number;
  qaQuestion?: string;
  qaAnswer?: string;
  ingestStatus: IngestStatus;
  ingestError?: string;
  ingestedAtUtc?: string;
  settingsOverrideJson?: string;
  metadataJson?: string;
  recallCount?: number;
  lastRecalledAtUtc?: string;
  createdAtUtc: string;
  updatedAtUtc?: string;
  folderId?: string | null;
  folderPath?: string | null;
};

export type TopRecalledKbDocumentView = {
  documentId: string;
  knowledgeBaseId: string;
  sourceType: DocumentSourceType;
  fileName?: string;
  qaQuestion?: string;
  ingestStatus: IngestStatus;
  recallCount: number;
  lastRecalledAtUtc?: string;
  createdAtUtc: string;
};

// ── Segment ──

export type KbSegmentView = {
  id: string;
  documentId: string;
  segmentIndex: number;
  content: string;
  contentType?: string;
  metadataJson?: string;
  tokenCount?: number;
  createdAtUtc: string;
  updatedAtUtc?: string;
};

// ── Processing ──

export type StageProgressItem = {
  name: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  startedAt: string | null;
  endedAt: string | null;
};

export type ProcessingJobView = {
  id: string;
  documentId: string;
  currentStage: string;
  stageProgressJson?: string;
  stageProgress?: StageProgressItem[];
  errorMessage?: string;
  startedAtUtc?: string;
  completedAtUtc?: string;
  createdAtUtc: string;
  updatedAtUtc?: string;
};

export type DocumentIndexView = {
  id: string;
  documentId: string;
  indexType: IndexType;
  status: string;
  configJson?: string;
  statsJson?: string;
  builtAtUtc?: string;
  createdAtUtc: string;
  updatedAtUtc?: string;
};

// ── Search ──

export type KbSearchRequest = {
  query: string;
  topK?: number;
  searchMode?: 'hybrid' | 'vector' | 'fulltext';
};

export type KbSearchResult = {
  segmentId: string;
  documentId: string;
  content: string;
  score: number;
  metadataJson?: string;
  vectorScore?: number;
  fulltextScore?: number;
  documentName?: string;
  documentType?: string;
};

export type KbSearchResponse = {
  results: KbSearchResult[];
};

// ── Pagination ──

export type KbPagedResult<T> = {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
};

// ── QA Import ──

export type KbQaImportError = {
  rowNumber: number;
  question?: string;
  errorCode: string;
  message: string;
};

export type KbQaImportResult = {
  createdCount: number;
  updatedCount: number;
  skippedCount: number;
  errors: KbQaImportError[];
};
