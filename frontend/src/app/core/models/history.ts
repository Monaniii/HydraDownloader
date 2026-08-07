/**
 * History domain models mirroring the backend Pydantic schemas.
 */

export interface HistoryRecord {
  id: string;
  title: string;
  url: string;
  type: string;
  filePath: string;
  sizeBytes: number;
  duration: number;
  thumbnail: string;
  uploader: string;
  status: string;
  createdAt: number;
  completedAt: number | null;
}

export interface HistoryListResponse {
  items: HistoryRecord[];
  total: number;
}

export interface HistoryQuery {
  limit?: number;
  offset?: number;
  search?: string;
  type?: string;
}
