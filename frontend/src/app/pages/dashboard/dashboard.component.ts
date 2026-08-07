import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';

import { HealthService } from '../../core/services/health.service';

/**
 * Landing page: paste a URL, quick links to key features, and a
 * backend health indicator.
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent {
  private readonly health = inject(HealthService);
  private readonly router = inject(Router);

  url = '';
  analyzing = false;

  readonly isHealthy = this.health.isHealthy;
  readonly isChecking = this.health.isChecking;

  constructor() {
    this.health.check();
  }

  analyze(): void {
    if (!this.url.trim()) {
      return;
    }
    this.analyzing = true;
    this.router.navigate(['/analyze'], {
      queryParams: { url: this.url.trim() },
    });
  }
}
