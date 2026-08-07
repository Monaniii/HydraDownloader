import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { Subscription, debounceTime, distinctUntilChanged, Subject } from 'rxjs';

import { HistoryService } from '../../core/services/history.service';
import { HistoryRecord } from '../../core/models/history';
import { humanBytes, formatDuration } from '../../shared/utils/format';

/**
 * History page: lists downloaded items with search, type filter, open
 * folder, delete record, clear history, and re-download.
 */
@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    FormsModule,
  ],
  templateUrl: './history.component.html',
  styleUrls: ['./history.component.css'],
})
export class HistoryComponent implements OnInit, OnDestroy {
  private readonly historyService = inject(HistoryService);
  private readonly search$ = new Subject<string>();
  private readonly subscriptions: Subscription[] = [];

  protected readonly columns = ['thumbnail', 'title', 'type', 'size', 'status', 'date', 'actions'];

  records: HistoryRecord[] = [];
  total = 0;
  search = '';
  typeFilter = '';

  ngOnInit(): void {
    this.load();
    this.subscriptions.push(
      this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe(() => {
        this.load();
      }),
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach((sub) => sub.unsubscribe());
  }

  onSearchChange(value: string): void {
    this.search$.next(value);
  }

  onTypeChange(): void {
    this.load();
  }

  load(): void {
    this.historyService
      .list({ search: this.search || undefined, type: this.typeFilter || undefined, limit: 200 })
      .subscribe((res) => {
        this.records = res.items;
        this.total = res.total;
      });
  }

  deleteRecord(id: string): void {
    this.historyService.delete(id).subscribe(() => this.load());
  }

  clearAll(): void {
    this.historyService.clear().subscribe(() => this.load());
  }

  openFolder(record: HistoryRecord): void {
    // Electron will expose opening the containing folder via IPC.
    const win = window as unknown as {
      hydra?: { openFolder?: (path: string) => void };
    };
    if (win.hydra?.openFolder && record.filePath) {
      win.hydra.openFolder(record.filePath);
    }
  }

  typeIcon(type: string): string {
    if (type === 'audio') {
      return 'music_note';
    }
    if (type === 'playlist') {
      return 'playlist_play';
    }
    return 'movie';
  }

  protected readonly humanBytes = humanBytes;
  protected readonly formatDuration = formatDuration;
}
