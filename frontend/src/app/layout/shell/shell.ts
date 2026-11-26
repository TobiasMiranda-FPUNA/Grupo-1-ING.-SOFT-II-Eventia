import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../services/auth';
import { operacionesPara } from '../../core/operaciones';

// Layout común de las pantallas autenticadas: barra superior con el menú
// filtrado por rol, el usuario en sesión y el botón para cerrar sesión.
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private auth = inject(AuthService);
  private router = inject(Router);

  usuario = this.auth.usuario;

  constructor() {
    // Actualiza los datos de la sesión guardada (roles, cédula) al entrar al
    // área privada. Un token vencido lo resuelve el interceptor (401 → login).
    if (this.auth.isLoggedIn()) {
      this.auth.refrescarPerfil().subscribe({ error: () => undefined });
    }
  }
  menuAbierto = signal(false);

  menu = computed(() => {
    this.usuario();
    return operacionesPara((...r) => this.auth.hasRole(...r)).filter(op => op.enMenu && !op.proximamente);
  });

  iniciales = computed(() => {
    const u = this.usuario();
    return u ? `${u.nombres.charAt(0)}${u.apellidos.charAt(0)}`.toUpperCase() : '';
  });

  cerrarSesion(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
