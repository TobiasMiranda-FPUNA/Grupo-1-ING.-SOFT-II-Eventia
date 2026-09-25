import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Roles } from './pages/roles/roles';
import { Eventos } from './pages/eventos/eventos';
import { EventoForm } from './pages/evento-form/evento-form';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: Login },
  { path: 'roles', component: Roles },
  { path: 'eventos', component: Eventos },
  { path: 'eventos/nuevo', component: EventoForm },
  { path: 'eventos/:id/editar', component: EventoForm },
  { path: '**', redirectTo: 'login' },
];
