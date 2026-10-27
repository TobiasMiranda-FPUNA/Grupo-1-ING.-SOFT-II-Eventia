import { HttpClient, HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { BaseHttpService } from './base-http';

class DummyService extends BaseHttpService<{ id: number }> {
  protected baseUrl = '/api/dummy';
}

describe('BaseHttpService', () => {
  let service: DummyService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = new DummyService(TestBed.inject(HttpClient));
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('propaga el HttpErrorResponse con su código de estado', () => {
    let recibido: HttpErrorResponse | undefined;
    service.getAll().subscribe({ error: err => (recibido = err) });

    httpMock.expectOne('/api/dummy').flush({ detail: 'x' }, { status: 409, statusText: 'Conflict' });

    expect(recibido?.status).toBe(409);
  });
});
