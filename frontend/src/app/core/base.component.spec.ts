import { BaseComponent } from './base.component';

class DummyComponent extends BaseComponent {}

describe('BaseComponent', () => {
  it('should create an instance', () => {
    expect(new DummyComponent()).toBeTruthy();
  });
});
