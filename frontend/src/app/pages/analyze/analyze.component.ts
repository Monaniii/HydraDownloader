import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

/**
 * Analyze page (placeholder for Phase 2).
 * Will display metadata extracted by the backend Analyzer service.
 */
@Component({
  selector: 'app-analyze',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule],
  templateUrl: './analyze.component.html',
  styleUrls: ['./analyze.component.css'],
})
export class AnalyzeComponent {}
