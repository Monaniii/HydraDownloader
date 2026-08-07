import { ErrorHandler, Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

/**
 * Global error handler for the application.
 *
 * Centralises logging and user-facing error reporting so that no
 * component or service has to duplicate error handling logic.
 */
@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private readonly snackBar = inject(MatSnackBar);

  handleError(error: unknown): void {
    // Always log the full error to the console for debugging.
    console.error('[Hydra] Unhandled error:', error);

    const message =
      error instanceof Error ? error.message : 'An unexpected error occurred.';

    this.snackBar.open(message, 'Dismiss', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }
}
