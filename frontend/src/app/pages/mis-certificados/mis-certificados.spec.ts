import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { MisCertificados } from './mis-certificados';
import { MiCertificado } from '../../services/certificados';
import { environment } from '../../../environments/environment';

const API = `${environment.apiUrl}/certificados`;

function cert(cambios: Partial<MiCertificado>): MiCertificado {
  return {
    id_inscripcion: 1, id_participante: 1, participante: 'Hugo Villagra', email: 'hugo@fpuna.edu.py',
    estado_inscripcion: 'confirmada', actividades_evento: 4, asistencias_presentes: 4,
    porcentaje_asistencia: 100, minimo_requerido: 75, elegible: true,
    certificado_emitido: false, codigo_validacion: null, fecha_emision: null,
    id_evento: 1, evento: 'Congreso', fecha_inicio_evento: '2026-11-10', fecha_fin_evento: '2026-11-12',
    ...cambios,
  };
}

describe('MisCertificados', () => {
  let http: HttpTestingController;

  function crear(lista: MiCertificado[]) {
    TestBed.configureTestingModule({
      imports: [MisCertificados],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(MisCertificados);
    fixture.detectChanges();
    http.expectOne(`${API}/mios`).flush(lista);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('muestra cada inscripción con su estado y solo ofrece descargar las emitidas', () => {
    const fixture = crear([
      cert({ id_inscripcion: 1, evento: 'Congreso', certificado_emitido: true, codigo_validacion: 'ABC123' }),
      cert({ id_inscripcion: 2, evento: 'Taller', elegible: true }),
      cert({ id_inscripcion: 3, evento: 'Seminario', elegible: false, porcentaje_asistencia: 25, fecha_fin_evento: '2026-01-01' }),
      cert({ id_inscripcion: 4, evento: 'Jornada', estado_inscripcion: 'lista_de_espera', elegible: false }),
    ]);
    const c = fixture.componentInstance;

    expect(c.certificados().map(x => c.textoEstado(x))).toEqual([
      'Emitido', 'Pendiente de emisión', 'No alcanzó el mínimo', 'En lista de espera',
    ]);
    expect(c.emitidos()).toBe(1);
    const botones = fixture.nativeElement.querySelectorAll('button.btn-primary');
    expect(botones.length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('ABC123');
  });

  it('descarga el PDF del certificado propio', () => {
    const fixture = crear([cert({ certificado_emitido: true, codigo_validacion: 'ABC123' })]);
    const c = fixture.componentInstance;
    URL.createObjectURL = () => 'blob:x';
    URL.revokeObjectURL = () => undefined;

    c.descargar(c.certificados()[0]);
    const req = http.expectOne(`${API}/mios/1/documento`);
    expect(req.request.responseType).toBe('blob');
    req.flush(new Blob(['%PDF'], { type: 'application/pdf' }));

    expect(c.descargandoId()).toBeNull();
    expect(c.error()).toBeNull();
  });

  it('sin inscripciones invita a inscribirse', () => {
    const fixture = crear([]);
    expect(fixture.nativeElement.textContent).toContain('Todavía no tenés inscripciones');
  });
});
