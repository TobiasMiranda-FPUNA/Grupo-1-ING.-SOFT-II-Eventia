
import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Roles } from './pages/roles/roles';
import { Eventos } from './pages/eventos/eventos';
import { EventoForm } from './pages/evento-form/evento-form';
import { Expositores } from './pages/expositores/expositores';
import { InscripcionPublica } from './pages/inscripcion-publica/inscripcion-publica';
import { AgendaPublica } from './pages/agenda-publica/agenda-publica';
import { CertificadoVerificacion } from './pages/certificado-verificacion/certificado-verificacion';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: Login },
  { path: 'roles', component: Roles },
  { path: 'eventos', component: Eventos },
  { path: 'eventos/nuevo', component: EventoForm },
  { path: 'eventos/:id/editar', component: EventoForm },
  { path: 'expositores', component: Expositores },
  { path: 'inscripciones', component: InscripcionPublica },
  { path: 'eventos/:id/inscribirse', component: InscripcionPublica },
  { path: 'agenda', component: AgendaPublica },
  { path: 'eventos/:id/agenda', component: AgendaPublica },
  { path: 'certificados/verificar', component: CertificadoVerificacion },
  { path: 'certificados/verificar/:codigo', component: CertificadoVerificacion },
  { path: '**', redirectTo: 'login' },
];
