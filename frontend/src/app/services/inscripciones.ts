import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface RolParticipantePublico {
  id_rol_participante: number;
  nombre: string;
  descripcion: string | null;
}

export interface InscripcionPayload {
  id_evento: number;
  id_rol_participante: number;
  documento: string | null;
  nombres: string;
  apellidos: string;
  email: string;
  institucion: string | null;
}

export interface InscripcionResultado {
  id_inscripcion: number;
  id_evento: number;
  id_participante: number;
  id_rol_participante: number;
  fecha_inscripcion: string;
  estado: 'confirmada' | 'lista_de_espera' | string;
}

@Injectable({ providedIn: 'root' })
export class InscripcionesService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/inscripciones`;

  getRolesPublicos(): Observable<RolParticipantePublico[]> {
    return this.http.get<RolParticipantePublico[]>(
      `${this.apiUrl}/roles-participante`
    );
  }

  inscribir(data: InscripcionPayload): Observable<InscripcionResultado> {
    return this.http.post<InscripcionResultado>(this.apiUrl, data);
  }
}
