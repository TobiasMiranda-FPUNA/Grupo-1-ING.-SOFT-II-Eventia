import { RolBase } from './base.model';

class DummyRol extends RolBase {}

describe('RolBase', () => {
  it('should create an instance', () => {
    expect(new DummyRol()).toBeTruthy();
  });
});
