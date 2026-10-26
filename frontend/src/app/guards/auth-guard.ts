import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

// Exige sesión iniciada; si no la hay (o el token venció) redirige al login.
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isLoggedIn() ? true : inject(Router).createUrlTree(['/login']);
};

// Exige alguno de los roles indicados en data.roles de la ruta; si el
// usuario no los tiene, vuelve a la pantalla de inicio.
export const roleGuard: CanActivateFn = (route) => {
  const roles: string[] = route.data['roles'] ?? [];
  const auth = inject(AuthService);
  return roles.length === 0 || auth.hasRole(...roles) ? true : inject(Router).createUrlTree(['/inicio']);
};

// Evita mostrar el login a quien ya tiene sesión iniciada.
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isLoggedIn() ? inject(Router).createUrlTree(['/inicio']) : true;
};
