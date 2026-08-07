import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiService } from './api.service';
import { DownloadRequest, QueueItem } from '../models/download';

/**
 * Owns the live download queue state and exposes the control operations
 * (start, pause, resume, cancel, retry, remove).
 *
 * Queue state is held in a signal and can be updated either by direct
 * REST responses or by WebSocket events being merged into this service.
 */
@Injectable({ providedIn: 'root' })
export class QueueService {
  private readonly api = inject(ApiService);
  private readonly items = signal<QueueItem[]>([]);

  /** Read-only observable accessor to the current queue. */
  readonly queue = computed(() => this.items());

  /** Queue items that are actively running (not terminal). */
  readonly activeItems = computed(() =>
    this.items().filter(
      (it) =>
        !['COMPLETED', 'FAILED', 'CANCELLED'].includes(it.status),
    ),
  );

  /** Queue items in a terminal state. */
  readonly completedItems = computed(() =>
    this.items().filter((it) => it.status === 'COMPLETED'),
  );

  /** Load the current queue from the backend. */
  refresh(): void {
    this.api.get<QueueItem[]>('/queue').subscribe((items) => this.items.set(items));
  }

  /** Replace or merge a single item into the queue signal. */
  upsert(item: QueueItem): void {
    this.items.update((prev) => {
      const idx = prev.findIndex((it) => it.id === item.id);
      if (idx === -1) {
        return [...prev, item];
      }
      const copy = [...prev];
      copy[idx] = item;
      return copy;
    });
  }

  /** Remove an item from the local queue signal. */
  removeLocal(id: string): void {
    this.items.update((prev) => prev.filter((it) => it.id !== id));
  }

  download(request: DownloadRequest): Observable<QueueItem> {
    const endpoint =
      request.media_type === 'audio'
        ? '/download/audio'
        : request.media_type === 'playlist'
          ? '/download/playlist'
          : '/download/video';
    return this.api.post<QueueItem>(endpoint, request).pipe(
      tap((item) => this.upsert(item)),
    );
  }

  pause(id: string): Observable<QueueItem> {
    return this.queueControl('pause', id);
  }

  resume(id: string): Observable<QueueItem> {
    return this.queueControl('resume', id);
  }

  retry(id: string): Observable<QueueItem> {
    return this.queueControl('retry', id);
  }

  cancel(id: string): Observable<QueueItem> {
    return this.api.delete<QueueItem>(`/queue/cancel?id=${id}`).pipe(
      tap((item) => this.upsert(item)),
    );
  }

  remove(id: string): Observable<{ removed: boolean; id: string }> {
    return this.api
      .delete<{ removed: boolean; id: string }>(`/queue/${id}`)
      .pipe(tap(() => this.removeLocal(id)));
  }

private queueControl(action: 'pause' | 'resume' | 'retry', id: string): Observable<QueueItem> {
    return this.api.post<QueueItem>(`/queue/${id}/${action}`, {}).pipe(
      tap((item) => this.upsert(item)),
    );
  }
}
