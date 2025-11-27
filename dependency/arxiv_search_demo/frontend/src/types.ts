export type SortBy = "relevance" | "submittedDate" | "lastUpdatedDate";
export type SortOrder = "ascending" | "descending";
export type DateMode = "submitted" | "updated" | null;

export interface ArxivPaper {
  arxiv_id: string;
  version?: string | null;
  title: string;
  summary?: string | null;
  authors: string[];
  primary_category?: string | null;
  categories: string[];
  published?: string | null;
  updated?: string | null;
  pdf_url?: string | null;
  abs_url?: string | null;
  doi?: string | null;
  journal_ref?: string | null;
}

export interface SearchRequest {
  all_terms?: string | null;
  title?: string | null;
  abstract?: string | null;
  author?: string | null;
  categories?: string[] | null;
  date_mode?: DateMode;
  date_from?: string | null;
  date_to?: string | null;
  sort_by?: SortBy;
  sort_order?: SortOrder;
  max_results?: number;
  id_list?: string[] | null;
}

export interface SavePaperRequest {
  paper: ArxivPaper;
  tags?: string | null;
  note?: string | null;
}

export interface SavedPaper {
  id: number;
  paper_id: number;
  tags?: string | null;
  note?: string | null;
  created_at: string;
  updated_at: string;
  paper: ArxivPaper;
}

export interface SavedListResponse {
  items: SavedPaper[];
  page: number;
  page_size: number;
  total: number;
}
