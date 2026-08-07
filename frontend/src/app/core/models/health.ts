/**
 * Health status payload returned by the backend `GET /health` endpoint.
 */
export interface HealthStatus {
  status: string;
  app: string;
  version: string;
}
