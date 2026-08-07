import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subscription } from 'rxjs';

import { QueueService } from '../../core/services/queue.service';
import { DownloadSocketService } from '../../core/services/download-socket.service';
import { QueueItem, DownloadEvent } from '../../core/models/download';
import { humanBytes, formatDuration } from '../../shared/utils/format';

/**
 * Downloads page: live queue with progress bars, speed/ETA, status labels
 * and per-item controls (pause/resume/cancel/retry/remove).
 *
 * Queue items are updated from two sources: the REST snapshot and the
 * WebSocket event stream for near-real-time progress.
 */
@Component({
  selector: 'app-downloads',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
MatTableModule,
    MatChipsModule,
    MatTooltipModule,
  ],
  templateUrl: './downloads.component.html',
  styleUrls: ['./downloads.component.css'],
})
export class DownloadsComponent implements OnInit, OnDestroy {
  private readonly queueService = inject(QueueService);
  private readonly socketService = inject(DownloadSocketService);
  private readonly subscriptions: Subscription[] = [];

  protected readonly columns = ['thumbnail', 'title', 'progress', 'speed', 'eta', 'status', 'actions'];
  readonly queue = this.queueService.queue;

  ngOnInit(): void {
    this.queueService.refresh();
    this.subscriptions.push(
      this.socketService.stream().subscribe((event) => this.handleEvent(event)),
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach((sub) => sub.unsubscribe());
  }

  private handleEvent(event: DownloadEvent): void {
    if (event.item) {
      this.queueService.upsert(event.item);
    }
  }

  pause(id: string): void {
    this.queueService.pause(id).subscribe();
  }

  resume(id: string): void {
    this.queueService.resume(id).subscribe();
  }

  cancel(id: string): void {
    this.queueService.cancel(id).subscribe();
  }

  retry(id: string): void {
    this.queueService.retry(id).subscribe();
  }

  remove(id: string): void {
    this.queueService.remove(id).subscribe();
  }

  isActive(item: QueueItem): boolean {
    return ['DOWNLOADING', 'INITIALIZING', 'ANALYZING', 'POST_PROCESSING'].includes(item.status);
  }

  typeIcon(item: QueueItem): string {
    if (item.media_type === 'audio') {
      return 'music_note';
    }
    if (item.media_type === 'playlist') {
      return 'playlist_play';
    }
    return 'movie';
  }

  statusLabel(item: QueueItem): string {
    return item.status.replace('_', ' ');
  }

  statusClass(state: string): string {
    const map: Record<string, string> = {
      COMPLETED: 'completed',
      FAILED: 'failed',
      CANCELLED: 'cancelled',
      PAUSED: 'paused',
      DOWNLOADING: 'active',
      INITIALIZING: 'active',
      ANALYZING: 'active',
      POST_PROCESSING: 'active',
      QUEUED: 'queued',
      RETRYING: 'retrying',
    };
    return map[state] ?? 'queued';
  }

  progressValue(item: QueueItem): number {
    return Math.min(100, Math.max(0, item.progress));
  }

  protected readonly humanBytes = humanBytes;
  protected readonly formatDuration = formatDuration;
}
