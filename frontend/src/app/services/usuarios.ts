import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// Usuario tal como lo devuelve GET /users (UsuarioAdminResponse).
export interface UsuarioAdmin {
  id_usuario: number;
  nombres: string;
  apellidos: string;
  email: string;
  activo: boolean;
  roles: string[];
}

// Datos para crear una cuenta (UsuarioCreate en el backend).
export interface UsuarioNuevo {
  nombres: string;
  apellidos: string;
  email: string;
  password: string;
  id_rol_sistema: number;
}

// Rol de sistema que devuelve GET /roles/sistema (RoleResponse).
export interface RolSistema {
  id: number;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
}

// Gestión de cuentas de usuario. Todos los endpoints exigen el rol
// administrador en el backend.
@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/users`;

  listar(): Observable<UsuarioAdmin[]> {
    return this.http.get<UsuarioAdmin[]>(this.baseUrl);
  }

  crear(usuario: UsuarioNuevo): Observable<UsuarioAdmin> {
    return this.http.post<UsuarioAdmin>(this.baseUrl, usuario);
  }

  eliminar(idUsuario: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${idUsuario}`);
  }

  listarRolesSistema(): Observable<RolSistema[]> {
    return this.http.get<RolSistema[]>(`${environment.apiUrl}/roles/sistema`);
  }
}
