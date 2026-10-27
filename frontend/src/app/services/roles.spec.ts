import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { RolesService } from './roles-service';

describe('RolesService', () => {
  let service: RolesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    service = TestBed.inject(RolesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
