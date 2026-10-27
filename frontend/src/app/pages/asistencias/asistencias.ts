import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { Actividad, ActividadesService } from '../../services/actividades';
import {
  AsistenciaParticipante,
  AsistenciasService,
  EstadoAsistencia,
} from '../../services/asistencias';
import { Evento, EventosService } from '../../services/eventos';

@Component({
  selector: 'app-asistencias',
  imports: [CommonModule, FormsModule],
  templateUrl: './asistencias.html',
  styleUrl: './asistencias.scss',
})
export class Asistencias implements OnInit {
  private eventosService = inject(EventosService);
  private actividadesService = inject(ActividadesService);
  private asistenciasService = inject(AsistenciasService);

  eventos = signal<Evento[]>([]);
  actividades = signal<Actividad[]>([]);
  participantes = signal<AsistenciaParticipante[]>([]);

  eventoId: number | null = null;
  actividadId: number | null = null;

  cargando = signal(false);
  guardando = signal(false);
  mensaje = signal<string | null>(null);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.eventosService.getEventos().subscribe({
      next: eventos => this.eventos.set(eventos),
      error: () => this.error.set('No se pudieron cargar los eventos.'),
    });
  }

  cambiarEvento(): void {
    this.actividadId = null;
    this.actividades.set([]);
    this.participantes.set([]);
    this.mensaje.set(null);
    this.error.set(null);

    if (!this.eventoId) return;

    this.actividadesService.getActividadesPorEvento(this.eventoId).subscribe({
      next: actividades => this.actividades.set(actividades),
      error: () => this.error.set('No se pudo cargar la agenda del evento.'),
    });
  }

  cambiarActividad(): void {
    this.participantes.set([]);
    this.mensaje.set(null);
    this.error.set(null);

    if (!this.eventoId || !this.actividadId) return;

    this.cargando.set(true);
    this.asistenciasService
      .getParticipantes(this.eventoId, this.actividadId)
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: participantes => this.participantes.set(participantes),
        error: err => this.error.set(
          err?.error?.detail || 'No se pudo cargar la lista de participantes.'
        ),
      });
  }

  marcar(participante: AsistenciaParticipante, estado: EstadoAsistencia): void {
    this.participantes.update(items =>
      items.map(item =>
        item.id_inscripcion === participante.id_inscripcion
          ? { ...item, estado_asistencia: estado }
          : item
      )
    );
    this.mensaje.set(null);
  }

  marcarTodos(estado: EstadoAsistencia): void {
    this.participantes.update(items =>
      items.map(item => ({ ...item, estado_asistencia: estado }))
    );
    this.mensaje.set(null);
  }

  pendientes(): number {
    return this.participantes().filter(p => !p.estado_asistencia).length;
  }

  guardar(): void {
    if (!this.actividadId || this.participantes().length === 0) return;

    if (this.pendientes() > 0) {
      this.error.set('Marcá presente o ausente para todos los participantes antes de guardar.');
      return;
    }

    const registros = this.participantes().map(p => ({
      id_inscripcion: p.id_inscripcion,
      estado: p.estado_asistencia as EstadoAsistencia,
    }));

    this.error.set(null);
    this.mensaje.set(null);
    this.guardando.set(true);

    this.asistenciasService
      .guardar(this.actividadId, registros)
      .pipe(finalize(() => this.guardando.set(false)))
      .subscribe({
        next: response => {
          this.mensaje.set(
            `Asistencia guardada correctamente para ${response.registros_guardados} participante(s).`
          );
          this.cambiarActividad();
        },
        error: err => this.error.set(
          err?.error?.detail || 'No se pudo guardar la asistencia.'
        ),
      });
  }
}
