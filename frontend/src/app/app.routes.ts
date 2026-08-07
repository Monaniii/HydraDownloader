import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layout/main-layout.component';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./pages/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent
          ),
},
      {
        path: 'status',
        loadComponent: () =>
          import('./pages/status/status.component').then((m) => m.StatusComponent),
      },
      {
        path: 'analyze',
        loadComponent: () =>
          import('./pages/analyze/analyze.component').then((m) => m.AnalyzeComponent),
      },
      {
        path: 'downloads',
        loadComponent: () =>
          import('./pages/downloads/downloads.component').then((m) => m.DownloadsComponent),
      },
      {
        path: 'history',
        loadComponent: () =>
          import('./pages/history/history.component').then((m) => m.HistoryComponent),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./pages/settings/settings.component').then((m) => m.SettingsComponent),
      },
      {
        path: '**',
        redirectTo: '',
      },
    ],
  },
];
