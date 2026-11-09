import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import {
  MetricasEvento,
  MetricasEventoResumen,
  MetricasService,
} from '../../services/metricas';

// Segmento de un gráfico (dona o barra apilada).
export interface Segmento {
  etiqueta: string;
  valor: number;
  color: string;
  porcentaje: number;
  // Desplazamiento y largo sobre una circunferencia de 100 unidades (dona).
  inicio: number;
  largo: number;
}

// Colores fijos por estado: cada estado conserva su color aunque otro sea 0.
const ESTADOS_INSCRIPCION = [
  { clave: 'confirmadas', etiqueta: 'Confirmadas', color: '#2a78d6' },
  { clave: 'lista_de_espera', etiqueta: 'Lista de espera', color: '#eb6834' },
  { clave: 'pendientes', etiqueta: 'Pendientes', color: '#1baf7a' },
  { clave: 'canceladas', etiqueta: 'Canceladas', color: '#eda100' },
  { clave: 'rechazadas', etiqueta: 'Rechazadas', color: '#e87ba4' },
] as const;

const ESTADOS_ASISTENCIA = [
  { clave: 'presentes', etiqueta: 'Presentes', color: '#16a34a' },
  { clave: 'ausentes', etiqueta: 'Ausentes', color: '#dc2626' },
  { clave: 'sin_registro', etiqueta: 'Sin registro', color: '#cbd5e1' },
] as const;

// Separación entre segmentos de la dona, en unidades de la circunferencia.
const GAP_DONA = 0.8;

function segmentos(items: { etiqueta: string; valor: number; color: string }[]): Segmento[] {
  const total = items.reduce((acc, i) => acc + i.valor, 0);
  const visibles = items.filter(i => i.valor > 0).length;
  let inicio = 0;
  return items.map(i => {
    const porcentaje = total ? (i.valor * 100) / total : 0;
    const largo = i.valor > 0 && visibles > 1 ? Math.max(porcentaje - GAP_DONA, 0.3) : porcentaje;
    const seg = { ...i, porcentaje, inicio, largo };
    inicio += porcentaje;
    return seg;
  });
}

// Panel de control (HU09): indicadores generales de todos los eventos y el
// detalle de inscripciones, cupos y asistencia del evento seleccionado.
@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private metricasService = inject(MetricasService);

  resumen = signal<MetricasEventoResumen[]>([]);
  detalle = signal<MetricasEvento | null>(null);

  eventoId: number | null = null;
  cargandoResumen = signal(false);
  cargandoDetalle = signal(false);
  error = signal<string | null>(null);

  // Indicadores generales calculados sobre el resumen de eventos.
  totales = computed(() => {
    const eventos = this.resumen();
    const cupos = eventos.reduce((acc, e) => acc + e.cupo_maximo, 0);
    const confirmados = eventos.reduce((acc, e) => acc + e.inscriptos_confirmados, 0);
    const conActividades = eventos.filter(e => e.total_actividades > 0 && e.inscriptos_confirmados > 0);
    return {
      eventos: eventos.length,
      publicados: eventos.filter(e => e.estado === 'publicado').length,
      borradores: eventos.filter(e => e.estado !== 'publicado').length,
      confirmados,
      listaEspera: eventos.reduce((acc, e) => acc + e.lista_de_espera, 0),
      cupos,
      ocupacion: cupos ? (confirmados * 100) / cupos : 0,
      asistencia: conActividades.length
        ? conActividades.reduce((acc, e) => acc + e.porcentaje_asistencia, 0) / conActividades.length
        : 0,
      actividades: eventos.reduce((acc, e) => acc + e.total_actividades, 0),
    };
  });

  segmentosInscripciones = computed(() => {
    const d = this.detalle();
    if (!d) return [];
    return segmentos(ESTADOS_INSCRIPCION.map(e => ({
      etiqueta: e.etiqueta,
      valor: d.inscripciones[e.clave],
      color: e.color,
    })));
  });

  segmentosAsistencia = computed(() => {
    const d = this.detalle();
    if (!d) return [];
    return segmentos(ESTADOS_ASISTENCIA.map(e => ({
      etiqueta: e.etiqueta,
      valor: d.asistencia[e.clave],
      color: e.color,
    })));
  });

  ngOnInit(): void {
    this.cargarResumen();
  }

  cargarResumen(): void {
    this.error.set(null);
    this.cargandoResumen.set(true);
    this.metricasService
      .getResumenEventos()
      .pipe(finalize(() => this.cargandoResumen.set(false)))
      .subscribe({
        next: eventos => {
          this.resumen.set(eventos);
          // Por defecto se muestra el evento más reciente.
          if (!this.eventoId && eventos.length) this.seleccionar(eventos[0].id_evento);
          else if (this.eventoId) this.cargarDetalle();
        },
        error: err => this.error.set(err?.error?.detail || 'No se pudieron cargar las métricas.'),
      });
  }

  seleccionar(id: number): void {
    this.eventoId = id;
    this.cargarDetalle();
  }

  cargarDetalle(): void {
    this.detalle.set(null);
    if (!this.eventoId) return;

    this.cargandoDetalle.set(true);
    this.metricasService
      .getDashboardEvento(this.eventoId)
      .pipe(finalize(() => this.cargandoDetalle.set(false)))
      .subscribe({
        next: detalle => this.detalle.set(detalle),
        error: err => this.error.set(err?.error?.detail || 'No se pudo cargar el detalle del evento.'),
      });
  }

  // Ancho de barra acotado a 0–100 (la ocupación no supera el cupo, pero se protege igual).
  ancho(porcentaje: number): number {
    return Math.min(Math.max(porcentaje, 0), 100);
  }

  // Semáforo de ocupación/asistencia usado en los indicadores.
  nivel(porcentaje: number): 'alto' | 'medio' | 'bajo' {
    if (porcentaje >= 75) return 'alto';
    if (porcentaje >= 40) return 'medio';
    return 'bajo';
  }
}
