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

@Injectable({ providedIn: 'root' })
export class CertificadosService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/certificados`;

  verificar(codigo: string): Observable<CertificadoVerificado> {
    return this.http.get<CertificadoVerificado>(
      `${this.apiUrl}/verificar/${encodeURIComponent(codigo.trim())}`
    );
  }
}
