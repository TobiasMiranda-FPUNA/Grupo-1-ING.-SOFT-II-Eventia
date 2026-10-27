import { ROLES } from '../services/auth';

// Operación del sistema que se ofrece al usuario en la pantalla de inicio y
// en la barra de navegación, según sus roles.
export interface Operacion {
  titulo: string;
  descripcion: string;
  icono: string;
  ruta: string;
  // Roles que pueden usarla; vacío = cualquier usuario autenticado.
  roles: string[];
  // Aparece en la barra de navegación superior.
  enMenu?: boolean;
  // Funcionalidad planificada pero aún no implementada (se muestra deshabilitada).
  proximamente?: boolean;
  historia: string;
}

const { ADMINISTRADOR, ORGANIZADOR, PARTICIPANTE, CONFERENCISTA, ACREDITACION } = ROLES;

export const OPERACIONES: Operacion[] = [
  {
    titulo: 'Roles y parámetros',
    descripcion: 'Administrá los roles del sistema y los tipos de participante.',
    icono: '⚙',
    ruta: '/roles',
    roles: [ADMINISTRADOR],
    enMenu: true,
    historia: 'HU02',
  },
  {
    titulo: 'Nuevo evento',
    descripcion: 'Creá un evento indicando tipo, fechas, lugar, cupo y política de inscripción.',
    icono: '＋',
    ruta: '/eventos/nuevo',
    roles: [ORGANIZADOR],
    historia: 'HU03',
  },
  {
    titulo: 'Catálogo de eventos',
    descripcion: 'Consultá y filtrá los eventos registrados en Eventia.',
    icono: '▦',
    ruta: '/eventos',
    roles: [],
    enMenu: true,
    historia: 'HU03',
  },
  {
    titulo: 'Agenda del evento',
    descripcion: 'Revisá el cronograma de actividades por día y sala.',
    icono: '🗓',
    ruta: '/agenda',
    roles: [],
    enMenu: true,
    historia: 'HU06',
  },
  {
    titulo: 'Expositores',
    descripcion: 'Registrá conferencistas y asignalos a las actividades.',
    icono: '🎤',
    ruta: '/expositores',
    roles: [ORGANIZADOR, ADMINISTRADOR, CONFERENCISTA],
    enMenu: true,
    historia: 'HU05',
  },
  {
    titulo: 'Inscripción a eventos',
    descripcion: 'Inscribite a un evento disponible y obtené tu comprobante.',
    icono: '✎',
    ruta: '/inscripciones',
    roles: [PARTICIPANTE, ORGANIZADOR],
    historia: 'HU04',
  },
  {
    titulo: 'Registro de asistencia',
    descripcion: 'Marcá presentes y ausentes por cada actividad del evento.',
    icono: '✔',
    ruta: '/asistencias',
    roles: [ACREDITACION, ORGANIZADOR, ADMINISTRADOR],
    enMenu: true,
    historia: 'HU07',
  },
  {
    titulo: 'Certificados',
    descripcion: 'Consultá elegibilidad, generá y descargá certificados de participación.',
    icono: '🏅',
    ruta: '/certificados',
    roles: [ORGANIZADOR, ADMINISTRADOR],
    enMenu: true,
    historia: 'HU08',
  },
  {
    titulo: 'Dashboard del evento',
    descripcion: 'Indicadores de inscriptos, cupos y asistencia en tiempo real.',
    icono: '📊',
    ruta: '/dashboard',
    roles: [ORGANIZADOR],
    proximamente: true,
    historia: 'HU09',
  },
];

export function operacionesPara(hasRole: (...roles: string[]) => boolean): Operacion[] {
  return OPERACIONES.filter(op => op.roles.length === 0 || hasRole(...op.roles));
}
