/**
 * Shared formatting utilities used across the frontend.
 */

/** Format a byte count into a compact human-readable size. */
export function humanBytes(value: number | undefined | null): string {
  if (!value || value <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let amount = value;
  let unit = units[0];
  for (let i = 0; i < units.length && amount >= 1024; i++) {
    amount /= 1024;
    unit = units[i + 1] ?? units[units.length - 1];
  }
  return `${amount.toFixed(amount < 10 && unit !== 'B' ? 1 : 0)} ${unit}`;
}

/** Format a number of seconds as mm:ss or hh:mm:ss. */
export function formatDuration(seconds: number | undefined | null): string {
  const total = Math.floor((seconds ?? 0));
  if (total <= 0) {
    return '';
  }
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${m}:${String(s).padStart(2, '0')}`;
}

/** Format a number of seconds as a friendly ETA string. */
export function formatEta(seconds: number | undefined | null): string {
  return formatDuration(seconds);
}

