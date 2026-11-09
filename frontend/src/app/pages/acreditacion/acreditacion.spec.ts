import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { Actividad } from '../../services/actividades';
import { AsistenciaParticipante } from '../../services/asistencias';
import { Acreditacion, actividadSugerida, coincide } from './acreditacion';

const API = environment.apiUrl;

function participante(
  id: number,
  nombre: string,
  estado: AsistenciaParticipante['estado_asistencia'] = null
): AsistenciaParticipante {
  return {
    id_inscripcion: id,
    id_participante: id,
    participante: nombre,
    email: `${nombre.split(' ')[0].toLowerCase()}@example.com`,
    estado_inscripcion: 'confirmada',
    estado_asistencia: estado,
  };
}

function actividad(id: number, fecha: string, inicio: string, fin: string): Actividad {
  return {
    id_actividad: id,
    id_evento: 1,
    id_categoria: 1,
    titulo: `Actividad ${id}`,
    fecha,
    hora_inicio: inicio,
    hora_fin: fin,
  };
}

describe('coincide', () => {
  const ana = participante(12, 'Ana Gómez');

  it('ignora tildes y mayúsculas', () => {
    expect(coincide(ana, 'GOMEZ')).toBe(true);
  });

  it('acepta palabras en cualquier orden', () => {
    expect(coincide(ana, 'gómez ana')).toBe(true);
    expect(coincide(ana, 'gómez luis')).toBe(false);
  });

  it('busca por correo y por número de inscripción exacto', () => {
    expect(coincide(ana, 'ana@example')).toBe(true);
    expect(coincide(ana, '#12')).toBe(true);
    expect(coincide(ana, '1')).toBe(false);
  });
});

describe('actividadSugerida', () => {
  const ahora = new Date(2026, 10, 10, 10, 15);
  const actividades = [
    actividad(1, '2026-11-10', '09:00:00', '10:00:00'),
    actividad(2, '2026-11-10', '10:00:00', '11:00:00'),
    actividad(3, '2026-11-10', '14:00:00', '15:00:00'),
    actividad(4, '2026-11-11', '09:00:00', '10:00:00'),
  ];

  it('elige la actividad en curso', () => {
    expect(actividadSugerida(actividades, ahora)?.id_actividad).toBe(2);
  });

  it('si no hay una en curso, elige la próxima del día', () => {
    expect(actividadSugerida(actividades, new Date(2026, 10, 10, 12, 0))?.id_actividad).toBe(3);
  });

  it('fuera de los días del evento no sugiere ninguna', () => {
    expect(actividadSugerida(actividades, new Date(2026, 10, 20, 9, 0))).toBeUndefined();
  });
});

describe('Acreditacion', () => {
  let fixture: ComponentFixture<Acreditacion>;
  let component: Acreditacion;
  let http: HttpTestingController;

  beforeEach(async () => {
    // En Node puede no haber localStorage; el componente funciona igual.
    globalThis.localStorage?.clear();
    await TestBed.configureTestingModule({
      imports: [Acreditacion],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Acreditacion);
    component = fixture.componentInstance;
    fixture.detectChanges();

    // Con un único evento y una única actividad se seleccionan solos.
    http.expectOne(`${API}/eventos`).flush([
      { id_evento: 1, nombre: 'Congreso', fecha_inicio: '2026-11-10', fecha_fin: '2026-11-11' },
    ]);
    http.expectOne(`${API}/eventos/1/agenda`).flush([
      actividad(5, '2026-11-10', '09:00:00', '10:00:00'),
    ]);
    http.expectOne(`${API}/asistencias/eventos/1/actividades/5`).flush([
      participante(1, 'Ana Gómez'),
      participante(2, 'Luis Benítez', 'ausente'),
      participante(3, 'Ana Duarte', 'presente'),
    ]);
  });

  afterEach(() => http.verify());

  it('carga la actividad y muestra el progreso', () => {
    expect(component.actividadId()).toBe(5);
    expect(component.total()).toBe(3);
    expect(component.acreditados()).toBe(1);
    expect(component.porcentaje()).toBe(33);
  });

  it('acredita con el alta individual y lo agrega a recientes', () => {
    component.acreditar(component.participantes()[0]);

    const req = http.expectOne(`${API}/asistencias`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      id_evento: 1,
      id_actividad: 5,
      id_inscripcion: 1,
      estado: 'presente',
    });
    req.flush({ id_asistencia: 9, id_inscripcion: 1, id_actividad: 5, estado: 'presente' });

    expect(component.participantes()[0].estado_asistencia).toBe('presente');
    expect(component.recientes().map(r => r.id_inscripcion)).toEqual([1]);
    expect(component.aviso()?.tipo).toBe('ok');
  });

  it('si otro dispositivo ya lo registró (409), actualiza la marca', () => {
    component.acreditar(component.participantes()[0]);

    http.expectOne(`${API}/asistencias`).flush(
      { detail: 'La asistencia ya fue registrada para esta actividad' },
      { status: 409, statusText: 'Conflict' }
    );
    const update = http.expectOne(`${API}/asistencias/actividades/5/registrar`);
    expect(update.request.body).toEqual({ registros: [{ id_inscripcion: 1, estado: 'presente' }] });
    update.flush({ id_actividad: 5, registros_guardados: 1 });

    expect(component.participantes()[0].estado_asistencia).toBe('presente');
  });

  it('una persona marcada como ausente se acredita actualizando su registro', () => {
    component.acreditar(component.participantes()[1]);

    http.expectOne(`${API}/asistencias/actividades/5/registrar`).flush({
      id_actividad: 5,
      registros_guardados: 1,
    });
    expect(component.participantes()[1].estado_asistencia).toBe('presente');
  });

  it('Enter acredita cuando hay una sola coincidencia', () => {
    component.busqueda.set('benitez');
    component.acreditarDesdeBusqueda();

    http.expectOne(`${API}/asistencias/actividades/5/registrar`).flush({
      id_actividad: 5,
      registros_guardados: 1,
    });
    expect(component.participantes()[1].estado_asistencia).toBe('presente');
    expect(component.busqueda()).toBe('');
  });

  it('Enter no adivina si hay varias coincidencias', () => {
    component.busqueda.set('ana');
    component.acreditarDesdeBusqueda();

    http.expectNone(`${API}/asistencias`);
    expect(component.aviso()?.tipo).toBe('info');
  });

  it('Enter con un acreditado no vuelve a registrarlo', () => {
    component.busqueda.set('#3');
    component.acreditarDesdeBusqueda();

    http.expectNone(`${API}/asistencias`);
    expect(component.aviso()?.texto).toContain('ya estaba acreditado');
  });

  it('marcar ausente corrige la marca', () => {
    component.marcarAusente(component.participantes()[2]);

    const req = http.expectOne(`${API}/asistencias/actividades/5/registrar`);
    expect(req.request.body).toEqual({ registros: [{ id_inscripcion: 3, estado: 'ausente' }] });
    req.flush({ id_actividad: 5, registros_guardados: 1 });

    expect(component.acreditados()).toBe(0);
  });

  it('el filtro de pendientes oculta a los acreditados', () => {
    component.filtro.set('pendientes');
    expect(component.resultados().map(p => p.id_inscripcion)).toEqual([1, 2]);
  });
});
