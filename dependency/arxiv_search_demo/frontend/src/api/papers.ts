import { apiClient } from "./client";
import type { SavePaperRequest, SavedListResponse, SavedPaper } from "../types";

export async function savePaper(payload: SavePaperRequest): Promise<SavedPaper> {
  const { data } = await apiClient.post<SavedPaper>("/papers/save", payload);
  return data;
}

export interface SavedQuery {
  page?: number;
  page_size?: number;
  keyword?: string;
  author?: string;
  category?: string;
  tag?: string;
  sort_by?: "created_at" | "published" | "updated";
  sort_order?: "asc" | "desc";
}

export async function fetchSaved(query: SavedQuery): Promise<SavedListResponse> {
  const { data } = await apiClient.get<SavedListResponse>("/papers/saved", { params: query });
  return data;
}

export async function fetchSavedDetail(id: number): Promise<SavedPaper> {
  const { data } = await apiClient.get<SavedPaper>(`/papers/${id}`);
  return data;
}

export async function updateSaved(id: number, payload: Partial<Pick<SavedPaper, "tags" | "note">>): Promise<SavedPaper> {
  const { data } = await apiClient.patch<SavedPaper>(`/papers/${id}`, payload);
  return data;
}

export async function deleteSavedRecord(id: number): Promise<void> {
  await apiClient.delete(`/papers/${id}`);
}
