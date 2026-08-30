import { HttpClient } from '@angular/common/http';
import { inject, Injectable, Service } from '@angular/core';
import { Observable } from 'rxjs';
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
    private apiUrl = 'http://localhost:8000/api/v1/roles-participante';

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
