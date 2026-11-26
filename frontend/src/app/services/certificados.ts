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
  // Solo viene en las respuestas que intentan enviar el certificado por correo.
  envio_correo?: EnvioCorreo | null;
}

export type EnvioCorreo = 'enviado' | 'error' | 'no_configurado';

// Certificado de una inscripción propia (GET /certificados/mios).
export interface MiCertificado extends CertificadoGestion {
  id_evento: number;
  evento: string;
  fecha_inicio_evento: string;
  fecha_fin_evento: string;
}

export interface EnvioCertificadosEvento {
  emitidos: number;
  enviados: number;
  con_error: number;
  sin_configurar: number;
  certificados: CertificadoGestion[];
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

  reenviar(idInscripcion: number): Observable<CertificadoGestion> {
    return this.http.post<CertificadoGestion>(
      `${this.apiUrl}/inscripcion/${idInscripcion}/enviar`,
      {}
    );
  }

  // Emite y envía por correo los certificados de quienes culminaron el evento.
  emitirYEnviarEvento(eventoId: number): Observable<EnvioCertificadosEvento> {
    return this.http.post<EnvioCertificadosEvento>(
      `${this.apiUrl}/evento/${eventoId}/emitir-y-enviar`,
      {}
    );
  }

  // Inscripciones del participante en sesión con el estado de su certificado.
  listarMios(): Observable<MiCertificado[]> {
    return this.http.get<MiCertificado[]>(`${this.apiUrl}/mios`);
  }

  // PDF de un certificado propio ya emitido.
  descargarMio(idInscripcion: number): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/mios/${idInscripcion}/documento`, { responseType: 'blob' });
  }

  verificar(codigo: string): Observable<CertificadoVerificado> {
    return this.http.get<CertificadoVerificado>(
      `${this.apiUrl}/verificar/${encodeURIComponent(codigo.trim())}`
    );
  }
}
