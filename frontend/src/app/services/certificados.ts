import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CertificadoVerificado {
  valido: boolean;
  codigo_validacion: string;
  tipo: string;
  fecha_emision: string;
  id_inscripcion: number;
  participante: string;
  evento: string;
  fecha_inicio_evento: string;
  fecha_fin_evento: string;
}

export interface CertificadoGestion {
  id_inscripcion: number;
  id_participante: number;
  participante: string;
  email: string;
  estado_inscripcion: string;
  actividades_evento: number;
  asistencias_presentes: number;
  porcentaje_asistencia: number;
  minimo_requerido: number;
  elegible: boolean;
  certificado_emitido: boolean;
  codigo_validacion: string | null;
  fecha_emision: string | null;
}

@Injectable({ providedIn: 'root' })
export class CertificadosService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/certificados`;

  listarPorEvento(eventoId: number): Observable<CertificadoGestion[]> {
    return this.http.get<CertificadoGestion[]>(
      `${this.apiUrl}/evento/${eventoId}/participantes`
    );
  }

  emitir(idInscripcion: number): Observable<CertificadoGestion> {
    return this.http.post<CertificadoGestion>(
      `${this.apiUrl}/emitir/${idInscripcion}`,
      {}
    );
  }

  verificar(codigo: string): Observable<CertificadoVerificado> {
    return this.http.get<CertificadoVerificado>(
      `${this.apiUrl}/verificar/${encodeURIComponent(codigo.trim())}`
    );
  }
}
