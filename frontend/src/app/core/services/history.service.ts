import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { HistoryListResponse, HistoryQuery } from '../models/history';

/**
 * Encapsulates history REST calls: listing (with search/filter/paging),
 * deleting a single record, and clearing all history.
 */
@Injectable({ providedIn: 'root' })
export class HistoryService {
  private readonly api = inject(ApiService);

  list(query: HistoryQuery = {}): Observable<HistoryListResponse> {
    const params = new URLSearchParams();
    if (query.limit !== undefined) {
      params.set('limit', String(query.limit));
    }
    if (query.offset !== undefined) {
      params.set('offset', String(query.offset));
    }
    if (query.search) {
      params.set('search', query.search);
    }
    if (query.type) {
      params.set('type', query.type);
    }
    const qs = params.toString();
    return this.api.get<HistoryListResponse>(`/history${qs ? `?${qs}` : ''}`);
  }

  delete(id: string): Observable<unknown> {
    return this.api.delete(`/history/${id}`);
  }

  clear(): Observable<unknown> {
    return this.api.delete('/history');
  }
}
