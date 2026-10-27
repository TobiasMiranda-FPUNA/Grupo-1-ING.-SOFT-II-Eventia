import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export type EstadoAsistencia = 'presente' | 'ausente';

export interface AsistenciaParticipante {
  id_inscripcion: number;
  id_participante: number;
  participante: string;
  email: string;
  estado_inscripcion: string;
  estado_asistencia: EstadoAsistencia | null;
}

export interface AsistenciaRegistro {
  id_inscripcion: number;
  estado: EstadoAsistencia;
}

export interface AsistenciaGuardado {
  id_actividad: number;
  registros_guardados: number;
}

export interface AsistenciaCreate {
  id_evento: number;
  id_actividad: number;
  id_inscripcion: number;
  estado: EstadoAsistencia;
}

export interface Asistencia {
  id_asistencia: number;
  id_inscripcion: number;
  id_actividad: number;
  estado: EstadoAsistencia;
  fecha_hora_registro: string;
}

@Injectable({ providedIn: 'root' })
export class AsistenciasService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/asistencias`;

  getParticipantes(
    eventoId: number,
    actividadId: number
  ): Observable<AsistenciaParticipante[]> {
    return this.http.get<AsistenciaParticipante[]>(
      `${this.apiUrl}/eventos/${eventoId}/actividades/${actividadId}`
    );
  }

  // Registra una asistencia individual. El backend valida que la actividad
  // y la inscripción pertenezcan al evento, y devuelve 409 si ya existe.
  registrar(data: AsistenciaCreate): Observable<Asistencia> {
    return this.http.post<Asistencia>(this.apiUrl, data);
  }

  guardar(
    actividadId: number,
    registros: AsistenciaRegistro[]
  ): Observable<AsistenciaGuardado> {
    return this.http.post<AsistenciaGuardado>(
      `${this.apiUrl}/actividades/${actividadId}/registrar`,
      { registros }
    );
  }
}
