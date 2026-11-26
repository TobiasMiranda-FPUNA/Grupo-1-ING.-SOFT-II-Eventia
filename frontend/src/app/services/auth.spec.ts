import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from './auth';
import { environment } from '../../environments/environment';
import { vi } from 'vitest';

// Almacenamiento en memoria: el entorno de pruebas no trae un localStorage completo.
function almacenamientoFalso(): Storage {
  const datos = new Map<string, string>();
  return {
    get length() { return datos.size; },
    clear: () => datos.clear(),
    getItem: (k: string) => datos.get(k) ?? null,
    key: (i: number) => [...datos.keys()][i] ?? null,
    removeItem: (k: string) => { datos.delete(k); },
    setItem: (k: string, v: string) => { datos.set(k, String(v)); },
  };
}

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    vi.stubGlobal('localStorage', almacenamientoFalso());
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.unstubAllGlobals();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('refrescarPerfil actualiza la sesión guardada con los datos del servidor', () => {
    const perfil = { id_usuario: 6, nombres: 'Hugo', apellidos: 'Villagra', email: 'hugo@fpuna.edu.py', documento: '232344', roles: ['participante'] };

    service.refrescarPerfil().subscribe();
    http.expectOne(`${environment.apiUrl}/users/me`).flush(perfil);

    expect(service.usuario()?.documento).toBe('232344');
    expect(JSON.parse(localStorage.getItem('current_user') ?? '{}').documento).toBe('232344');
  });
});
