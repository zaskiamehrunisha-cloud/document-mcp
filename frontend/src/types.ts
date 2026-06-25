export interface UploadResponse {
  job_id: string;
  document_id: number;
  filename: string;
  status: string;
  message: string;
}

export interface StatusResponse {
  job_id: string;
  document_id: number;
  status: string;
  progress: number;
  message?: string | null;
  rejection_note?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  discipline?: string;
  document_ids?: number[];
}

export interface SearchResult {
  chunk_id: number;
  content: string;
  document_id: number;
  document_number?: string;
  title?: string;
  discipline?: string;
  score: number;
  search_type: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface AskRequest {
  query: string;
  discipline?: string;
  document_ids?: number[];
}

export interface Citation {
  document_number: string;
  title?: string;
  page_or_sheet: string;
}

export interface AskResponse {
  answer: string;
  confidence: string;
  citations: Citation[];
  query: string;
  context_chunks_used: number;
}

export interface DocumentResponse {
  id: number;
  document_number?: string;
  title?: string;
  revision?: string;
  issue_status?: string;
  contract_number?: string;
  discipline?: string;
  page_count?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  page: number;
  page_size: number;
}