import { HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * HTTP interceptor that adds a JSON content-type header to outgoing
 * requests. Using a functional interceptor keeps it simple and testable.
 */
export const apiInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const cloned = req.clone({
    setHeaders: {
      'Content-Type': 'application/json',
    },
  });

  return next(cloned);
};
