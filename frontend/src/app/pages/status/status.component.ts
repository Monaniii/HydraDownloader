import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { HealthService } from '../../core/services/health.service';

/**
 * Backend status page showing live health information from the API.
 */
@Component({
  selector: 'app-status',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.css'],
})
export class StatusComponent {
  private readonly health = inject(HealthService);

  readonly status = this.health.currentStatus;
  readonly isChecking = this.health.isChecking;
  readonly isHealthy = this.health.isHealthy;

  constructor() {
    this.health.check();
  }

  refresh(): void {
    this.health.check();
  }
}
