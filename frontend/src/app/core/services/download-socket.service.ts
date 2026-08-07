import { Injectable } from '@angular/core';
import { Observable, Subject, timer } from 'rxjs';
import { webSocket, WebSocketSubject, WebSocketSubjectConfig } from 'rxjs/webSocket';

import { environment } from '../../../environments/environment';
import { DownloadEvent } from '../models/download';

/**
 * Streams download events from the backend over a WebSocket.
 *
 * The socket reconnects automatically with a fixed backoff and exposes a
 * Subject of {@link DownloadEvent}. Consumers subscribe once and receive
 * near-real-time progress without polling.
 */
@Injectable({ providedIn: 'root' })
export class DownloadSocketService {
  private readonly eventSubject$ = new Subject<DownloadEvent>();
  private socket$: WebSocketSubject<DownloadEvent> | null = null;
  private connected = false;

  constructor() {
    this.connect();
  }

  /** Connect (or reconnect) the underlying WebSocket. */
  connect(): void {
    const config: WebSocketSubjectConfig<DownloadEvent> = {
      url: `${environment.wsUrl}/ws/downloads`,
      serializer: (value) => JSON.stringify(value),
      deserializer: (msg) => JSON.parse(msg.data),
      openObserver: {
        next: () => {
          this.connected = true;
        },
      },
      closeObserver: {
        next: () => {
          this.connected = false;
          timer(1500).subscribe(() => this.connect());
        },
      },
    };
    this.socket$ = webSocket<DownloadEvent>(config);
    this.socket$.subscribe({
      next: (event) => this.eventSubject$.next(event),
      error: () => {
        this.connected = false;
      },
    });
  }

  /** Observable of real-time download events. */
  stream(): Observable<DownloadEvent> {
    return this.eventSubject$.asObservable();
  }

  /** Return whether the socket is currently connected. */
  isConnected(): boolean {
    return this.connected;
  }
}
