import { CommonModule } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  OnInit,
  afterNextRender,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, catchError, finalize, interval, throwError } from 'rxjs';

import { Actividad, ActividadesService } from '../../services/actividades';
import {
  AsistenciaParticipante,
  AsistenciasService,
  EstadoAsistencia,
} from '../../services/asistencias';
import { Evento, EventosService } from '../../services/eventos';

export type FiltroAcreditacion = 'todos' | 'pendientes' | 'acreditados';

interface Aviso {
  tipo: 'ok' | 'error' | 'info';
  texto: string;
}

interface Reciente {
  id_inscripcion: number;
  participante: string;
  hora: Date;
}

// Última selección de evento/actividad en este dispositivo, para que el
// personal no tenga que elegirla de nuevo al recargar la página.
const SELECCION_KEY = 'eventia.acreditacion.seleccion';
const RECARGA_MS = 30_000;
const MAX_RECIENTES = 6;

// Minúsculas y sin tildes: "Gómez" coincide con "gomez".
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

// Coincide si cada palabra buscada aparece en el nombre o el correo, o si
// la búsqueda es exactamente el número de inscripción (con o sin "#").
export function coincide(p: AsistenciaParticipante, busqueda: string): boolean {
  const consulta = normalizar(busqueda);
  if (!consulta) return true;
  if (consulta.replace(/^#/, '') === String(p.id_inscripcion)) return true;

  const texto = normalizar(`${p.participante} ${p.email}`);
  return consulta.split(/\s+/).every(palabra => texto.includes(palabra));
}

function fechaLocal(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function horaLocal(fecha: Date): string {
  return fecha.toTimeString().slice(0, 8);
}

export function estaEnCurso(actividad: Actividad, ahora = new Date()): boolean {
  const hora = horaLocal(ahora);
  return (
    actividad.fecha === fechaLocal(ahora) &&
    actividad.hora_inicio <= hora &&
    hora < actividad.hora_fin
  );
}

// Actividad que conviene preseleccionar: la que está en curso, si no la
// próxima de hoy, si no la última de hoy. Fuera del día del evento no
// sugiere ninguna (salvo que haya una sola actividad).
export function actividadSugerida(
  actividades: Actividad[],
  ahora = new Date()
): Actividad | undefined {
  const hoy = fechaLocal(ahora);
  const hora = horaLocal(ahora);
  const deHoy = actividades
    .filter(a => a.fecha === hoy)
    .sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));

  return (
    deHoy.find(a => estaEnCurso(a, ahora)) ??
    deHoy.find(a => a.hora_inicio > hora) ??
    deHoy.at(-1) ??
    (actividades.length === 1 ? actividades[0] : undefined)
  );
}

export function eventoSugerido(eventos: Evento[], ahora = new Date()): Evento | undefined {
  const hoy = fechaLocal(ahora);
  return eventos.find(e => e.fecha_inicio <= hoy && hoy <= e.fecha_fin);
}

@Component({
  selector: 'app-acreditacion',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './acreditacion.html',
  styleUrl: './acreditacion.scss',
})
export class Acreditacion implements OnInit {
  private eventosService = inject(EventosService);
  private actividadesService = inject(ActividadesService);
  private asistenciasService = inject(AsistenciasService);
  private destroyRef = inject(DestroyRef);
  private injector = inject(Injector);

  private buscador = viewChild<ElementRef<HTMLInputElement>>('buscador');
  private avisoTimer: ReturnType<typeof setTimeout> | undefined;

  eventos = signal<Evento[]>([]);
  actividades = signal<Actividad[]>([]);
  participantes = signal<AsistenciaParticipante[]>([]);

  eventoId = signal<number | null>(null);
  actividadId = signal<number | null>(null);
  busqueda = signal('');
  filtro = signal<FiltroAcreditacion>('todos');

  cargando = signal(false);
  actualizadoEn = signal<Date | null>(null);
  guardando = signal<ReadonlySet<number>>(new Set());
  recientes = signal<Reciente[]>([]);
  aviso = signal<Aviso | null>(null);
  error = signal<string | null>(null);

  total = computed(() => this.participantes().length);
  acreditados = computed(
    () => this.participantes().filter(p => p.estado_asistencia === 'presente').length
  );
  pendientes = computed(() => this.total() - this.acreditados());
  porcentaje = computed(() =>
    this.total() ? Math.round((this.acreditados() * 100) / this.total()) : 0
  );

  resultados = computed(() => {
    const filtro = this.filtro();
    const busqueda = this.busqueda();
    return this.participantes().filter(p => {
      const presente = p.estado_asistencia === 'presente';
      if (filtro === 'pendientes' && presente) return false;
      if (filtro === 'acreditados' && !presente) return false;
      return coincide(p, busqueda);
    });
  });

  actividadActual = computed(() =>
    this.actividades().find(a => a.id_actividad === this.actividadId())
  );

  ngOnInit(): void {
    this.eventosService.getEventos().subscribe({
      next: eventos => {
        this.eventos.set(eventos);
        const guardada = this.leerSeleccion();
        const evento =
          eventos.find(e => e.id_evento === guardada?.eventoId) ??
          eventoSugerido(eventos) ??
          (eventos.length === 1 ? eventos[0] : undefined);
        if (evento) this.cambiarEvento(evento.id_evento, guardada?.actividadId);
      },
      error: () => this.error.set('No se pudieron cargar los eventos.'),
    });

    // Varias personas pueden acreditar a la vez desde distintas puertas:
    // se actualiza la lista periódicamente para ver lo que marcaron los demás.
    interval(RECARGA_MS)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (this.actividadId() && this.guardando().size === 0) this.recargar(true);
      });
  }

  cambiarEvento(eventoId: number | null, actividadPreferida?: number | null): void {
    this.eventoId.set(eventoId);
    this.actividadId.set(null);
    this.actividades.set([]);
    this.limpiarActividad();

    if (!eventoId) return;

    this.actividadesService.getActividadesPorEvento(eventoId).subscribe({
      next: actividades => {
        this.actividades.set(actividades);
        const actividad =
          actividades.find(a => a.id_actividad === actividadPreferida) ??
          actividadSugerida(actividades);
        if (actividad) this.cambiarActividad(actividad.id_actividad);
      },
      error: () => this.error.set('No se pudo cargar la agenda del evento.'),
    });
  }

  cambiarActividad(actividadId: number | null): void {
    this.actividadId.set(actividadId);
    this.limpiarActividad();
    this.guardarSeleccion();
    if (actividadId) this.recargar(false);
  }

  recargar(silencioso: boolean): void {
    const eventoId = this.eventoId();
    const actividadId = this.actividadId();
    if (!eventoId || !actividadId) return;

    if (!silencioso) this.cargando.set(true);
    this.asistenciasService
      .getParticipantes(eventoId, actividadId)
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: participantes => {
          // Se descarta la respuesta si mientras tanto cambió la actividad.
          if (this.actividadId() !== actividadId) return;
          this.participantes.set(participantes);
          this.actualizadoEn.set(new Date());
          this.error.set(null);
          if (!silencioso) this.enfocarBuscador();
        },
        error: err => {
          if (!silencioso) {
            this.error.set(err?.error?.detail || 'No se pudo cargar la lista de participantes.');
          }
        },
      });
  }

  // Enter en el buscador: acredita si el número de inscripción coincide
  // exactamente o si hay una única coincidencia. Si no, no adivina.
  acreditarDesdeBusqueda(): void {
    const busqueda = this.busqueda();
    if (!normalizar(busqueda)) return;

    const numero = normalizar(busqueda).replace(/^#/, '');
    const porNumero = this.participantes().find(p => String(p.id_inscripcion) === numero);
    const candidatos = porNumero ? [porNumero] : this.participantes().filter(p => coincide(p, busqueda));

    if (candidatos.length === 0) {
      this.mostrarAviso('error', `No hay inscripciones confirmadas que coincidan con «${busqueda}».`);
    } else if (candidatos.length > 1) {
      this.mostrarAviso('info', `Hay ${candidatos.length} coincidencias: tocá la persona correcta en la lista.`);
    } else if (candidatos[0].estado_asistencia === 'presente') {
      this.mostrarAviso('info', `${candidatos[0].participante} ya estaba acreditado/a.`);
      this.limpiarBusqueda();
    } else {
      this.acreditar(candidatos[0]);
    }
  }

  acreditar(p: AsistenciaParticipante): void {
    this.cambiarEstado(p, 'presente');
  }

  marcarAusente(p: AsistenciaParticipante): void {
    this.cambiarEstado(p, 'ausente');
  }

  estaGuardando(p: AsistenciaParticipante): boolean {
    return this.guardando().has(p.id_inscripcion);
  }

  iniciales(nombre: string): string {
    return nombre
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(parte => parte[0].toUpperCase())
      .join('');
  }

  limpiarBusqueda(): void {
    this.busqueda.set('');
    this.enfocarBuscador();
  }

  private cambiarEstado(p: AsistenciaParticipante, estado: EstadoAsistencia): void {
    if (this.estaGuardando(p)) return;

    this.setGuardando(p.id_inscripcion, true);
    this.guardarEstado(p, estado)
      .pipe(finalize(() => this.setGuardando(p.id_inscripcion, false)))
      .subscribe({
        next: () => {
          this.participantes.update(items =>
            items.map(item =>
              item.id_inscripcion === p.id_inscripcion
                ? { ...item, estado_asistencia: estado }
                : item
            )
          );

          if (estado === 'presente') {
            this.recientes.update(items => [
              { id_inscripcion: p.id_inscripcion, participante: p.participante, hora: new Date() },
              ...items.filter(r => r.id_inscripcion !== p.id_inscripcion),
            ].slice(0, MAX_RECIENTES));
            this.mostrarAviso('ok', `✓ ${p.participante} acreditado/a.`);
            this.limpiarBusqueda();
          } else {
            this.recientes.update(items => items.filter(r => r.id_inscripcion !== p.id_inscripcion));
            this.mostrarAviso('info', `${p.participante} quedó como ausente.`);
          }
        },
        error: (err: HttpErrorResponse) =>
          this.mostrarAviso('error', err?.error?.detail || `No se pudo registrar a ${p.participante}.`),
      });
  }

  // Primera marca: alta individual (POST /asistencias). Si ya existía un
  // registro (409, por ejemplo marcado desde otro dispositivo) o se está
  // corrigiendo una marca previa, se actualiza con el registro por actividad.
  private guardarEstado(p: AsistenciaParticipante, estado: EstadoAsistencia): Observable<unknown> {
    const eventoId = this.eventoId()!;
    const actividadId = this.actividadId()!;
    const actualizar = () =>
      this.asistenciasService.guardar(actividadId, [{ id_inscripcion: p.id_inscripcion, estado }]);

    if (p.estado_asistencia !== null) return actualizar();

    return this.asistenciasService
      .registrar({
        id_evento: eventoId,
        id_actividad: actividadId,
        id_inscripcion: p.id_inscripcion,
        estado,
      })
      .pipe(
        catchError((err: HttpErrorResponse) =>
          err.status === 409 ? actualizar() : throwError(() => err)
        )
      );
  }

  private setGuardando(idInscripcion: number, activo: boolean): void {
    this.guardando.update(actual => {
      const siguiente = new Set(actual);
      if (activo) siguiente.add(idInscripcion);
      else siguiente.delete(idInscripcion);
      return siguiente;
    });
  }

  private mostrarAviso(tipo: Aviso['tipo'], texto: string): void {
    clearTimeout(this.avisoTimer);
    this.aviso.set({ tipo, texto });
    if (tipo !== 'error') {
      this.avisoTimer = setTimeout(() => this.aviso.set(null), 4000);
    }
  }

  private limpiarActividad(): void {
    this.participantes.set([]);
    this.recientes.set([]);
    this.busqueda.set('');
    this.aviso.set(null);
    this.error.set(null);
    this.actualizadoEn.set(null);
  }

  // Después del próximo render: al terminar la carga el buscador recién
  // aparece en la vista.
  private enfocarBuscador(): void {
    afterNextRender(() => this.buscador()?.nativeElement.focus(), { injector: this.injector });
  }

  private leerSeleccion(): { eventoId: number; actividadId: number | null } | null {
    try {
      const valor = localStorage.getItem(SELECCION_KEY);
      return valor ? JSON.parse(valor) : null;
    } catch {
      return null;
    }
  }

  private guardarSeleccion(): void {
    try {
      localStorage.setItem(
        SELECCION_KEY,
        JSON.stringify({ eventoId: this.eventoId(), actividadId: this.actividadId() })
      );
    } catch {
      // Sin almacenamiento disponible (modo privado): solo se pierde la comodidad.
    }
  }
}
