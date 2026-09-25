import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TipoEvento {
  id_tipo_evento: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
}

export interface PoliticaInscripcion {
  fecha_limite: string | null;
  requiere_aprobacion: boolean;
  permite_lista_espera: boolean;
  min_asistencia_certificado: number;
}

export interface Evento {
  id_evento: number;
  id_tipo_evento: number;
  nombre: string;
  descripcion: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  lugar: string | null;
  cupo_maximo: number;
  estado: 'borrador' | 'publicado';
  politica: PoliticaInscripcion | null;
}

export interface EventoPayload {
  id_tipo_evento: number;
  nombre: string;
  descripcion: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  lugar: string | null;
  cupo_maximo: number;
  estado: 'borrador' | 'publicado';
  politica: PoliticaInscripcion;
}

@Injectable({ providedIn: 'root' })
export class EventosService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/eventos`;

  getEventos(filters?: { q?: string; estado?: string; id_tipo_evento?: number }): Observable<Evento[]> {
    let params = new HttpParams();
    if (filters?.q) params = params.set('q', filters.q);
    if (filters?.estado) params = params.set('estado', filters.estado);
    if (filters?.id_tipo_evento) params = params.set('id_tipo_evento', filters.id_tipo_evento);
    return this.http.get<Evento[]>(this.apiUrl, { params });
  }

  getEvento(id: number): Observable<Evento> {
    return this.http.get<Evento>(`${this.apiUrl}/${id}`);
  }

  getTiposEvento(): Observable<TipoEvento[]> {
    return this.http.get<TipoEvento[]>(`${this.apiUrl}/tipos`);
  }

  createEvento(data: EventoPayload): Observable<Evento> {
    return this.http.post<Evento>(this.apiUrl, data);
  }

  updateEvento(id: number, data: EventoPayload): Observable<Evento> {
    return this.http.put<Evento>(`${this.apiUrl}/${id}`, data);
  }
}
