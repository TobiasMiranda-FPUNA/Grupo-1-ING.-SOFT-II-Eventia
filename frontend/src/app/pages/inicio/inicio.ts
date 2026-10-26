import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth';
import { operacionesPara } from '../../core/operaciones';

// Pantalla de bienvenida: saluda al usuario en sesión y le muestra las
// operaciones disponibles según sus roles de sistema.
@Component({
  selector: 'app-inicio',
  imports: [RouterLink],
  templateUrl: './inicio.html',
  styleUrl: './inicio.scss',
})
export class Inicio {
  private auth = inject(AuthService);

  usuario = this.auth.usuario;

  saludo = computed(() => {
    const hora = new Date().getHours();
    if (hora < 12) return 'Buenos días';
    if (hora < 19) return 'Buenas tardes';
    return 'Buenas noches';
  });

  operaciones = computed(() => {
    this.usuario();
    return operacionesPara((...r) => this.auth.hasRole(...r));
  });

  disponibles = computed(() => this.operaciones().filter(op => !op.proximamente));
  proximas = computed(() => this.operaciones().filter(op => op.proximamente));
}
