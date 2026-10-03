import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ActividadAsignada {
  id_actividad: number;
  id_evento: number;
  titulo: string;
  fecha: string;
}

export interface Conferencista {
  id_conferencista?: number;
  nombres: string;
  apellidos: string;
  email: string;
  institucion: string;
  especialidad: string;
  biografia: string;
  activo?: boolean;

  // Actividades a las que está asociado el expositor.
  actividades?: ActividadAsignada[];
}

@Injectable({
  providedIn: 'root'
})
export class ConferencistasService {
  private http = inject(HttpClient);

  private apiUrl =
    `${environment.apiUrl}/conferencistas`;

  getConferencistas(): Observable<Conferencista[]> {
    return this.http.get<Conferencista[]>(
      this.apiUrl
    );
  }

  createConferencista(
    conferencista: Conferencista
  ): Observable<Conferencista> {
    return this.http.post<Conferencista>(
      this.apiUrl,
      conferencista
    );
  }

  updateConferencista(
    id: number,
    conferencista: Partial<Conferencista>
  ): Observable<Conferencista> {
    return this.http.patch<Conferencista>(
      `${this.apiUrl}/${id}`,
      conferencista
    );
  }

  deleteConferencista(
    id: number
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/${id}`
    );
  }
}