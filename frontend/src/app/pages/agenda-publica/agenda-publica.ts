import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { Actividad, ActividadesService } from '../../services/actividades';
import { Evento, EventosService } from '../../services/eventos';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-agenda-publica',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './agenda-publica.html',
  styleUrl: './agenda-publica.scss',
})
export class AgendaPublica implements OnInit {
  private route = inject(ActivatedRoute);
  private eventosService = inject(EventosService);
  private actividadesService = inject(ActividadesService);
  private auth = inject(AuthService);

  // Con sesión vuelve a la pantalla principal; sin sesión, al login.
  rutaInicio = this.auth.isLoggedIn() ? '/inicio' : '/login';
  textoInicio = this.auth.isLoggedIn() ? 'Volver al inicio' : 'Iniciar sesión';

  eventos = signal<Evento[]>([]);
  actividades = signal<Actividad[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);
  eventoId = signal(0);
  diaSeleccionado = signal('');

  dias = computed(() =>
    [...new Set(this.actividades().map(a => a.fecha))].sort()
  );

  salas = computed(() => {
    const dia = this.diaSeleccionado();
    return [...new Set(
      this.actividades()
        .filter(a => !dia || a.fecha === dia)
        .map(a => a.lugar?.trim() || 'Sin sala definida')
    )].sort();
  });

  eventoActual = computed(() =>
    this.eventos().find(e => e.id_evento === this.eventoId()) ?? null
  );

  ngOnInit(): void {
    const idRuta = Number(this.route.snapshot.paramMap.get('id')) || 0;

    this.eventosService.getEventos({ estado: 'publicado' }).subscribe({
      next: eventos => {
        this.eventos.set(eventos);
        const inicial = eventos.some(e => e.id_evento === idRuta)
          ? idRuta
          : (eventos[0]?.id_evento ?? 0);
        this.eventoId.set(inicial);
        this.cargarAgenda();
      },
      error: () => {
        this.error.set('No fue posible cargar los eventos publicados.');
        this.cargando.set(false);
      },
    });
  }

  cambiarEvento(value: string | number): void {
    this.eventoId.set(Number(value));
    this.cargarAgenda();
  }

  cargarAgenda(): void {
    const id = this.eventoId();
    this.error.set(null);

    if (!id) {
      this.actividades.set([]);
      this.cargando.set(false);
      return;
    }

    this.cargando.set(true);
    this.actividadesService.getActividadesPorEvento(id)
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: actividades => {
          this.actividades.set(actividades);
          this.diaSeleccionado.set(
            [...new Set(actividades.map(a => a.fecha))].sort()[0] ?? ''
          );
        },
        error: () => this.error.set('No fue posible cargar la agenda del evento.'),
      });
  }

  actividadesSala(sala: string): Actividad[] {
    return this.actividades()
      .filter(a =>
        a.fecha === this.diaSeleccionado() &&
        (a.lugar?.trim() || 'Sin sala definida') === sala
      )
      .sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  }

  etiquetaDia(fecha: string): string {
    const [anio, mes, dia] = fecha.split('-').map(Number);
    return new Intl.DateTimeFormat('es-PY', {
      weekday: 'short', day: '2-digit', month: 'short'
    }).format(new Date(anio, mes - 1, dia));
  }
}
