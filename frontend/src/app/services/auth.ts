import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface LoginCredentials {
    email: string;
    password_hash: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private http = inject(HttpClient);
    // URL local de la API FastAPI desarrollada por tu compañero
    private apiUrl = 'http://localhost:8000/api/v1/auth';

    login(credentials: LoginCredentials): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(`${this.apiUrl}/login`, credentials).pipe(
        tap(response => {
            if (response.access_token) {
            localStorage.setItem('access_token', response.access_token);
            }
        })
        );
    }

    logout(): void {
        localStorage.removeItem('access_token');
    }

    isLoggedIn(): boolean {
        return !!localStorage.getItem('access_token');
    }
}