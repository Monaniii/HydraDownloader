import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from './api.service';
import { HealthStatus } from '../models/health';

/**
 * Service that checks backend health and exposes it as a signal.
 * Used by the UI to indicate whether the FastAPI backend is reachable.
 */
@Injectable({ providedIn: 'root' })
export class HealthService {
  private readonly api = inject(ApiService);

  private readonly status = signal<HealthStatus | null>(null);
  private readonly checking = signal(false);

  readonly currentStatus = this.status.asReadonly();
  readonly isChecking = this.checking.asReadonly();

  /** Derived signal: true when the backend reports a healthy status. */
  readonly isHealthy = computed(() => this.status()?.status === 'ok');

  async check(): Promise<void> {
    this.checking.set(true);
    try {
      const result = await firstValueFrom(this.api.get<HealthStatus>('/health'));
      this.status.set(result);
    } catch {
      this.status.set(null);
    } finally {
      this.checking.set(false);
    }
  }
}
