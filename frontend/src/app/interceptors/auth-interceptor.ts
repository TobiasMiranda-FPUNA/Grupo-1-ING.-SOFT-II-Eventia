import { HttpInterceptorFn } from '@angular/common/http';

// Adjunta el token guardado en el login (ver AuthService) como header
// "Authorization: Bearer <token>" en cada petición, requerido por los
// endpoints protegidos del backend (ej: /api/v1/roles/participantes).
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('access_token');

  if (!token) {
    return next(req);
  }

  return next(req.clone({
    setHeaders: { Authorization: `Bearer ${token}` }
  }));
};
