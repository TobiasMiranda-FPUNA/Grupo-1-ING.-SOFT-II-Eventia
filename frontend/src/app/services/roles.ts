import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
export interface ParticipantRole {
    id?: number;
    nombre: string;
    descripcion: string;
    activo: boolean;
    enUso?: boolean; // Para controlar la regla de negocio
}

@Injectable({
  providedIn: 'root'
})


export class RolesService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiUrl}/roles/participantes`;

    getRoles(): Observable<ParticipantRole[]> {
        return this.http.get<ParticipantRole[]>(this.apiUrl);
    }

    createRole(role: ParticipantRole): Observable<ParticipantRole> {
        return this.http.post<ParticipantRole>(this.apiUrl, role);
    }

    deleteRole(id: number): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/${id}`);
    }
}
