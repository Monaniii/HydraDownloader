/**
 * Download domain models mirroring the backend Pydantic schemas.
 */

export type DownloadType = 'video' | 'audio' | 'playlist';

export type DownloadState =
  | 'QUEUED'
  | 'INITIALIZING'
  | 'ANALYZING'
  | 'DOWNLOADING'
  | 'POST_PROCESSING'
  | 'PAUSED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'RETRYING';

export interface QueueItem {
  id: string;
  url: string;
  title: string;
  media_type: string;
  status: DownloadState;
  priority: number;
  progress: number;
  createdAt: number;
  error: string;
  resolution: string;
  filePath: string;
  sizeBytes: number;
  speed: string;
  eta: string;
  thumbnail: string;
  uploader: string;
  retries: number;
}

export interface ProgressUpdate {
  id: string;
  status: DownloadState;
  progress: number;
  downloadedBytes: number;
  totalBytes: number;
  speed: string;
  eta: string;
  title: string;
  error: string;
  resolution: string;
  fragment: number;
  elapsed: number;
  filename: string;
  retries: number;
}

export interface DownloadRequest {
  url: string;
  formatId?: string;
  outputFolder?: string;
  embedThumbnail?: boolean;
  embedMetadata?: boolean;
  subtitles?: boolean;
  playlist?: boolean;
  audioFormat?: string;
  audioQuality?: string;
  media_type?: DownloadType;
  video_format?: string;
  output_dir?: string;
  filename_template?: string;
  priority?: number;
}

export type DownloadEventType =
  | 'queued'
  | 'started'
  | 'progress'
  | 'paused'
  | 'resumed'
  | 'completed'
  | 'cancelled'
  | 'failed'
  | 'retrying'
  | 'snapshot';

export interface DownloadEvent {
  type: DownloadEventType;
  item: QueueItem;
  progress: ProgressUpdate | null;
}
