import { Routes } from '@angular/router';

import { Login } from './pages/login/login';
import { Inicio } from './pages/inicio/inicio';
import { Roles } from './pages/roles/roles';
import { Eventos } from './pages/eventos/eventos';
import { EventoForm } from './pages/evento-form/evento-form';
import { Expositores } from './pages/expositores/expositores';
import { Asistencias } from './pages/asistencias/asistencias';
import { Certificados } from './pages/certificados/certificados';

import { InscripcionPublica } from './pages/inscripcion-publica/inscripcion-publica';
import { AgendaPublica } from './pages/agenda-publica/agenda-publica';
import { CertificadoVerificacion } from './pages/certificado-verificacion/certificado-verificacion';

import { Shell } from './layout/shell/shell';
import { authGuard, guestGuard, roleGuard } from './guards/auth-guard';
import { ROLES } from './services/auth';

export const routes: Routes = [

  // LOGIN
  {
    path: 'login',
    component: Login,
    canActivate: [guestGuard],
  },

  // =========================
  // RUTAS PÚBLICAS
  // =========================

  {
    path: 'inscripciones',
    component: InscripcionPublica,
  },

  {
    path: 'eventos/:id/inscribirse',
    component: InscripcionPublica,
  },

  {
    path: 'agenda',
    component: AgendaPublica,
  },

  {
    path: 'eventos/:id/agenda',
    component: AgendaPublica,
  },

  {
    path: 'certificados/verificar',
    component: CertificadoVerificacion,
  },

  {
    path: 'certificados/verificar/:codigo',
    component: CertificadoVerificacion,
  },

  // =========================
  // ÁREA PRIVADA
  // =========================

  {
    path: '',
    component: Shell,
    canActivate: [authGuard],

    children: [

      {
        path: 'inicio',
        component: Inicio,
      },

      {
        path: 'roles',
        component: Roles,
        canActivate: [roleGuard],
        data: {
          roles: [ROLES.ADMINISTRADOR],
        },
      },

      {
        path: 'eventos',
        component: Eventos,
      },

      {
        path: 'eventos/nuevo',
        component: EventoForm,
        canActivate: [roleGuard],
        // Igual que el backend: solo el organizador crea/edita eventos.
        data: {
          roles: [
            ROLES.ORGANIZADOR,
          ],
        },
      },

      {
        path: 'eventos/:id/editar',
        component: EventoForm,
        canActivate: [roleGuard],
        // Igual que el backend: solo el organizador crea/edita eventos.
        data: {
          roles: [
            ROLES.ORGANIZADOR,
          ],
        },
      },

      {
        path: 'expositores',
        component: Expositores,
        canActivate: [roleGuard],
        data: {
          roles: [
            ROLES.ORGANIZADOR,
            ROLES.ADMINISTRADOR,
            ROLES.CONFERENCISTA,
          ],
        },
      },

      {
        path: 'asistencias',
        component: Asistencias,
        canActivate: [roleGuard],
        data: {
          roles: [
            ROLES.ORGANIZADOR,
            ROLES.ADMINISTRADOR,
            ROLES.ACREDITACION,
          ],
        },
      },

      {
        path: 'certificados',
        component: Certificados,
        canActivate: [roleGuard],
        data: {
          roles: [
            ROLES.ORGANIZADOR,
            ROLES.ADMINISTRADOR,
          ],
        },
      },

      {
        path: '',
        redirectTo: 'inicio',
        pathMatch: 'full',
      },
    ],
  },

  // =========================
  // RUTA NO ENCONTRADA
  // =========================

  {
    path: '**',
    redirectTo: 'login',
  },
];
