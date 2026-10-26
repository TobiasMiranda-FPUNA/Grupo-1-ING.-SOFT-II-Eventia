import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Inicio } from './pages/inicio/inicio';
import { Roles } from './pages/roles/roles';
import { Eventos } from './pages/eventos/eventos';
import { EventoForm } from './pages/evento-form/evento-form';
import { Expositores } from './pages/expositores/expositores';
import { Agenda } from './pages/agenda/agenda';
import { Shell } from './layout/shell/shell';
import { authGuard, guestGuard, roleGuard } from './guards/auth-guard';
import { ROLES } from './services/auth';

export const routes: Routes = [
  { path: 'login', component: Login, canActivate: [guestGuard] },
  {
    // Pantallas autenticadas: comparten la barra de navegación (Shell).
    path: '',
    component: Shell,
    canActivate: [authGuard],
    canActivateChild: [roleGuard],
    children: [
      { path: '', redirectTo: 'inicio', pathMatch: 'full' },
      { path: 'inicio', component: Inicio },
      { path: 'roles', component: Roles, data: { roles: [ROLES.ADMINISTRADOR] } },
      { path: 'eventos', component: Eventos },
      { path: 'eventos/nuevo', component: EventoForm, data: { roles: [ROLES.ORGANIZADOR] } },
      { path: 'eventos/:id/editar', component: EventoForm, data: { roles: [ROLES.ORGANIZADOR] } },
      {
        path: 'expositores',
        component: Expositores,
        data: { roles: [ROLES.ORGANIZADOR, ROLES.ADMINISTRADOR, ROLES.CONFERENCISTA] },
      },
      { path: 'agenda', component: Agenda },
    ],
  },
  { path: '**', redirectTo: 'inicio' },
];
