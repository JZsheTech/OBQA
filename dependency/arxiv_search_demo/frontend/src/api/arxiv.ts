import { apiClient } from "./client";
import type { ArxivPaper, SearchRequest } from "../types";

export async function searchArxiv(payload: SearchRequest): Promise<ArxivPaper[]> {
  const { data } = await apiClient.post<{ items: ArxivPaper[] }>("/arxiv/search", payload);
  return data.items;
}
