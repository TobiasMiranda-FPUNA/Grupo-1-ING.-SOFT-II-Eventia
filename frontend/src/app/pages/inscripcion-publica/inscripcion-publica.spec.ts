import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { InscripcionPublica } from './inscripcion-publica';
import { AuthService } from '../../services/auth';

const HUGO = { id_usuario: 6, nombres: 'Hugo', apellidos: 'Villagra', email: 'hugo@fpuna.edu.py' };

function authCon(roles: string[] | null) {
  const usuario = roles ? { ...HUGO, roles } : null;
  return {
    usuario: () => usuario,
    isLoggedIn: () => usuario !== null,
    hasRole: (...r: string[]) => (usuario?.roles ?? []).some(x => r.includes(x)),
  };
}

describe('InscripcionPublica', () => {
  let http: HttpTestingController;

  function crear(roles: string[] | null) {
    TestBed.configureTestingModule({
      imports: [InscripcionPublica],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useValue: authCon(roles) },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(InscripcionPublica);
    fixture.detectChanges();
    http.match(() => true).forEach(req =>
      req.flush(req.request.url.includes('roles')
        ? [{ id_rol_participante: 1, nombre: 'Asistente' }]
        : [{ id_evento: 10, nombre: 'Taller de Git', fecha_inicio: '2026-12-20' }]),
    );
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  afterEach(() => http.verify());

  it('un participante con sesión se inscribe con los datos de su cuenta, sin poder editarlos', () => {
    const c = crear(['participante']);
    const { nombres, apellidos, email } = c.form.controls;

    expect(c.datosDeCuenta).toBe(true);
    expect([nombres.value, apellidos.value, email.value]).toEqual(['Hugo', 'Villagra', 'hugo@fpuna.edu.py']);
    expect(nombres.disabled && apellidos.disabled && email.disabled).toBe(true);

    c.enviar();
    const req = http.expectOne(r => r.method === 'POST');
    expect(req.request.body).toMatchObject({ nombres: 'Hugo', apellidos: 'Villagra', email: 'hugo@fpuna.edu.py' });
    req.flush({ id_inscripcion: 1, estado: 'confirmada' });

    // Al iniciar otra inscripción, los datos de la cuenta se mantienen.
    c.nuevaInscripcion();
    expect(nombres.value).toBe('Hugo');
    expect(nombres.disabled).toBe(true);
  });

  it('el organizador puede inscribir a otra persona escribiendo sus datos', () => {
    const c = crear(['organizador']);

    expect(c.datosDeCuenta).toBe(false);
    expect(c.form.controls.nombres.enabled).toBe(true);
    expect(c.form.controls.nombres.value).toBe('');
  });

  it('sin sesión el formulario queda vacío y editable', () => {
    const c = crear(null);

    expect(c.datosDeCuenta).toBe(false);
    expect(c.form.controls.email.enabled).toBe(true);
  });
});
