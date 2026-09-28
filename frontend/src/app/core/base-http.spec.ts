import { TestBed } from '@angular/core/testing';
import { BaseHttp } from './base-http';

describe('BaseHttp', () => {
  let service: BaseHttp;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(BaseHttp);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
