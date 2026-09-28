import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
export type ID = number | string;

export abstract class BaseHttpService<T> {
    // Encapsulamiento: protected para que solo las clases hijas definan la URL
    protected abstract baseUrl: string;

    constructor(protected http: HttpClient) {}

    protected handleError(error: HttpErrorResponse): Observable<never> {
        console.error(`Error HTTP en ${this.baseUrl}:`, error);
        return throwError(() => new Error(error.message || 'Ocurrió un error en la comunicación con el servidor.'));
    }

    // Abstracción: T representa el modelo de datos (RolParticipante, Usuario, etc.)
    getAll(params?: Record<string, any>): Observable<T[]> {
        return this.http.get<T[]>(this.baseUrl, { params }).pipe(
        catchError(this.handleError.bind(this))
        );
    }

    getById(id: ID): Observable<T> {
        return this.http.get<T>(`${this.baseUrl}/${id}`).pipe(
        catchError(this.handleError.bind(this))
        );
    }

    create(item: T): Observable<T> {
        return this.http.post<T>(this.baseUrl, item).pipe(
        catchError(this.handleError.bind(this))
        );
    }

    update(id: ID, item: Partial<T>): Observable<T> {
        return this.http.put<T>(`${this.baseUrl}/${id}`, item).pipe(
        catchError(this.handleError.bind(this))
        );
    }

    delete(id: ID): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/${id}`).pipe(
        catchError(this.handleError.bind(this))
        );
    }
}