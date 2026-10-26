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
