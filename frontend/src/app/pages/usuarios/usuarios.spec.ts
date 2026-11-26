import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';

import { Usuarios } from './usuarios';
import { AuthService } from '../../services/auth';
import { environment } from '../../../environments/environment';

const API = environment.apiUrl;

describe('Usuarios', () => {
  let http: HttpTestingController;

  function crear() {
    const fixture = TestBed.createComponent(Usuarios);
    fixture.detectChanges();
    http.expectOne(`${API}/users`).flush([
      { id_usuario: 1, nombres: 'Ana', apellidos: 'Duarte', email: 'admin@eventia.test', activo: true, roles: ['administrador'] },
      { id_usuario: 2, nombres: 'Lucía', apellidos: 'Giménez', email: 'participante@eventia.test', activo: true, roles: ['participante'] },
    ]);
    http.expectOne(`${API}/roles/sistema`).flush([
      { id: 1, nombre: 'administrador', activo: true },
      { id: 3, nombre: 'participante', activo: true },
      { id: 9, nombre: 'viejo', activo: false },
    ]);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Usuarios],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { usuario: () => ({ id_usuario: 1, nombres: 'Ana', apellidos: 'Duarte', email: 'admin@eventia.test', roles: ['administrador'] }) } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lista los usuarios y ofrece solo roles activos', () => {
    const fixture = crear();
    const c = fixture.componentInstance;

    expect(c.usuarios().length).toBe(2);
    expect(c.roles().map(r => r.nombre)).toEqual(['administrador', 'participante']);
    // El administrador en sesión no tiene botón para eliminarse.
    const botones = fixture.nativeElement.querySelectorAll('button.btn-danger');
    expect(botones.length).toBe(1);
  });

  it('no envía el formulario si faltan datos', () => {
    const fixture = crear();
    fixture.componentInstance.crear();
    http.expectNone(`${API}/users`);
    expect(fixture.componentInstance.form.touched).toBe(true);
  });

  it('crea un usuario con correo, contraseña y rol', () => {
    const fixture = crear();
    const c = fixture.componentInstance;
    c.form.setValue({ nombres: 'María', apellidos: 'López', email: 'maria@eventia.test', password: 'Clave1234', id_rol_sistema: 3 });

    c.crear();
    const req = http.expectOne(r => r.method === 'POST' && r.url === `${API}/users`);
    expect(req.request.body).toEqual({ nombres: 'María', apellidos: 'López', email: 'maria@eventia.test', password: 'Clave1234', id_rol_sistema: 3 });
    req.flush({ id_usuario: 5, nombres: 'María', apellidos: 'López', email: 'maria@eventia.test', activo: true, roles: ['participante'] });

    http.expectOne(`${API}/users`).flush([]);
    expect(c.exito()).toContain('maria@eventia.test');
  });

  it('muestra el detalle del backend cuando el correo ya existe', () => {
    const fixture = crear();
    const c = fixture.componentInstance;
    c.form.setValue({ nombres: 'Ana', apellidos: 'D', email: 'admin@eventia.test', password: 'Clave1234', id_rol_sistema: 1 });

    c.crear();
    http.expectOne(r => r.method === 'POST').flush({ detail: 'Ya existe un usuario con ese correo' }, { status: 409, statusText: 'Conflict' });

    expect(c.error()).toBe('Ya existe un usuario con ese correo');
  });

  it('elimina un usuario después de confirmar', () => {
    const fixture = crear();
    const c = fixture.componentInstance;
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    c.eliminar(c.usuarios()[1]);
    http.expectOne(r => r.method === 'DELETE' && r.url === `${API}/users/2`).flush(null);

    expect(c.usuarios().map(u => u.id_usuario)).toEqual([1]);
  });
});
