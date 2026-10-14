import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface LoginCredentials {
    email: string;
    password: string;
}

// Datos del usuario autenticado que devuelve el backend (UserResponse).
export interface UsuarioSesion {
    id_usuario: number;
    nombres: string;
    apellidos: string;
    email: string;
    roles: string[];
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    user: UsuarioSesion;
}

// Nombres de los roles de sistema (tabla rol_sistema), en minúsculas, tal
// como los compara el backend en require_system_role.
export const ROLES = {
    ADMINISTRADOR: 'administrador',
    ORGANIZADOR: 'organizador',
    PARTICIPANTE: 'participante',
    CONFERENCISTA: 'conferencista',
    ACREDITACION: 'personal de acreditación',
} as const;

const TOKEN_KEY = 'access_token';
const USER_KEY = 'current_user';
const EXPIRES_KEY = 'token_expires_at';

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiUrl}/auth`;

    // Usuario en sesión, disponible para la vista (bienvenida, barra de navegación).
    readonly usuario = signal<UsuarioSesion | null>(this.leerUsuario());

    login(credentials: LoginCredentials): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${this.apiUrl}/login`, credentials).pipe(
        tap(response => {
            if (response.access_token) {
            localStorage.setItem(TOKEN_KEY, response.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(response.user));
            localStorage.setItem(EXPIRES_KEY, String(Date.now() + response.expires_in * 1000));
            this.usuario.set(response.user);
            }
        })
        );
    }

    logout(): void {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(EXPIRES_KEY);
        this.usuario.set(null);
    }

    isLoggedIn(): boolean {
        const expiresAt = Number(localStorage.getItem(EXPIRES_KEY) ?? 0);
        if (!localStorage.getItem(TOKEN_KEY) || !this.usuario() || Date.now() >= expiresAt) {
            if (this.usuario()) this.logout();
            return false;
        }
        return true;
    }

    // true si el usuario tiene al menos uno de los roles indicados.
    hasRole(...roles: string[]): boolean {
        const propios = (this.usuario()?.roles ?? []).map(r => r.toLowerCase());
        return roles.some(r => propios.includes(r.toLowerCase()));
    }

    private leerUsuario(): UsuarioSesion | null {
        try {
            const raw = localStorage.getItem(USER_KEY);
            return raw ? JSON.parse(raw) as UsuarioSesion : null;
        } catch {
            return null;
        }
    }
}
