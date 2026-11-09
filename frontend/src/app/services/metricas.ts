import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// Resumen de un evento que devuelve GET /metricas/eventos (MetricasEventoResumen).
export interface MetricasEventoResumen {
  id_evento: number;
  nombre: string;
  estado: string;
  fecha_inicio: string;
  cupo_maximo: number;
  inscriptos_confirmados: number;
  lista_de_espera: number;
  porcentaje_ocupacion: number;
  total_actividades: number;
  porcentaje_asistencia: number;
}

export interface MetricasInscripciones {
  total: number;
  confirmadas: number;
  lista_de_espera: number;
  pendientes: number;
  canceladas: number;
  rechazadas: number;
}

export interface MetricasCupos {
  cupo_maximo: number;
  ocupados: number;
  disponibles: number;
  porcentaje_ocupacion: number;
}

export interface MetricasAsistenciaActividad {
  id_actividad: number;
  titulo: string;
  fecha: string;
  hora_inicio: string;
  cupo: number;
  presentes: number;
  ausentes: number;
  sin_registro: number;
  porcentaje_asistencia: number;
}

export interface MetricasAsistencia {
  total_actividades: number;
  presentes: number;
  ausentes: number;
  sin_registro: number;
  porcentaje_asistencia: number;
  actividades: MetricasAsistenciaActividad[];
}

// Detalle de un evento que devuelve GET /eventos/{id}/dashboard.
export interface MetricasEvento {
  id_evento: number;
  nombre: string;
  estado: string;
  inscripciones: MetricasInscripciones;
  cupos: MetricasCupos;
  asistencia: MetricasAsistencia;
}

@Injectable({ providedIn: 'root' })
export class MetricasService {
  private http = inject(HttpClient);

  getResumenEventos(): Observable<MetricasEventoResumen[]> {
    return this.http.get<MetricasEventoResumen[]>(`${environment.apiUrl}/metricas/eventos`);
  }

  getDashboardEvento(eventoId: number): Observable<MetricasEvento> {
    return this.http.get<MetricasEvento>(`${environment.apiUrl}/eventos/${eventoId}/dashboard`);
  }
}
