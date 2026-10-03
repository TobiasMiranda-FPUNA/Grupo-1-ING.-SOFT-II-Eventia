
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Actividad {
  id_actividad: number;
  id_evento: number;
  id_categoria: number;
  titulo: string;
  descripcion?: string;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  lugar?: string;
  modalidad?: string;
  cupo?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ActividadesService {
  private http = inject(HttpClient);

  private apiUrl = `${environment.apiUrl}/actividades`;
  private eventosUrl = `${environment.apiUrl}/eventos`;

  getActividadesPorEvento(eventoId: number): Observable<Actividad[]> {
    return this.http.get<Actividad[]>(
      `${this.eventosUrl}/${eventoId}/agenda`
    );
  }

  asociarConferencista(
    actividadId: number,
    conferencistaId: number
  ): Observable<Actividad> {
    return this.http.post<Actividad>(
      `${this.apiUrl}/${actividadId}/conferencistas/${conferencistaId}`,
      {}
    );
  }
}
