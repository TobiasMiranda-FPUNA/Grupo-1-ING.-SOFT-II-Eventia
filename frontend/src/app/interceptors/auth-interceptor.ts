import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth';

// Adjunta el token guardado en el login (ver AuthService) como header
// "Authorization: Bearer <token>" en cada petición, requerido por los
// endpoints protegidos del backend (ej: /api/v1/roles/participantes).
// Si el backend responde 401 (token vencido o inválido) se cierra la
// sesión y se vuelve al login.
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('access_token');

  if (!token) {
    return next(req);
  }

  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req.clone({
    setHeaders: { Authorization: `Bearer ${token}` }
  })).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !req.url.endsWith('/auth/login')) {
        auth.logout();
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
