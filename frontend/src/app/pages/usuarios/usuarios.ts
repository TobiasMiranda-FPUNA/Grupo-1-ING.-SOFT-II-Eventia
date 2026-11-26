import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../services/auth';
import { RolSistema, UsuarioAdmin, UsuariosService } from '../../services/usuarios';

// Normaliza la cédula como el backend: sin puntos ni espacios y en mayúsculas.
export function normalizarDocumento(valor: string): string {
  return (valor ?? '').replace(/[\s.]/g, '').toUpperCase();
}

// Cédula válida: 3 a 20 caracteres entre dígitos, letras (pasaportes) y guiones,
// una vez quitados los puntos y espacios ("4.123.456" es válida).
function cedulaValida(control: AbstractControl): ValidationErrors | null {
  const valor = normalizarDocumento(control.value);
  if (!valor) return null; // de eso se encarga Validators.required
  return /^[A-Z0-9-]{3,20}$/.test(valor) ? null : { cedula: true };
}

// Pantalla de gestión de usuarios (solo administrador): lista las cuentas,
// permite crear una nueva con su rol de sistema y eliminar cuentas.
@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.scss',
})
export class Usuarios implements OnInit {
  private fb = inject(FormBuilder);
  private usuariosService = inject(UsuariosService);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  usuarios = signal<UsuarioAdmin[]>([]);
  roles = signal<RolSistema[]>([]);
  cargando = signal(false);
  guardando = signal(false);
  eliminandoId = signal<number | null>(null);
  error = signal<string | null>(null);
  exito = signal<string | null>(null);
  busqueda = signal('');

  idUsuarioActual = computed(() => this.auth.usuario()?.id_usuario ?? null);

  usuariosFiltrados = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return this.usuarios();
    return this.usuarios().filter(u =>
      `${u.nombres} ${u.apellidos} ${u.email} ${u.documento ?? ''} ${u.roles.join(' ')}`.toLowerCase().includes(texto),
    );
  });

  form = this.fb.nonNullable.group({
    nombres: ['', [Validators.required, Validators.maxLength(100)]],
    apellidos: ['', [Validators.required, Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email]],
    documento: ['', [Validators.required, cedulaValida]],
    password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
    id_rol_sistema: [0, [Validators.required, Validators.min(1)]],
  });

  ngOnInit(): void {
    this.cargarUsuarios();
    this.cargarRoles();
  }

  invalido(campo: keyof typeof this.form.controls): boolean {
    const control = this.form.controls[campo];
    return control.touched && control.invalid;
  }

  cargarUsuarios(): void {
    this.cargando.set(true);
    this.usuariosService
      .listar()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: lista => {
          this.usuarios.set(lista);
          this.cargando.set(false);
        },
        error: err => {
          this.usuarios.set([]);
          this.cargando.set(false);
          this.mostrarError(err, 'No se pudieron cargar los usuarios.');
        },
      });
  }

  cargarRoles(): void {
    this.usuariosService
      .listarRolesSistema()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: roles => this.roles.set(roles.filter(r => r.activo)),
        error: err => this.mostrarError(err, 'No se pudieron cargar los roles del sistema.'),
      });
  }

  crear(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.limpiarMensajes();
    this.guardando.set(true);
    const datos = this.form.getRawValue();

    this.usuariosService
      .crear({ ...datos, documento: normalizarDocumento(datos.documento), id_rol_sistema: Number(datos.id_rol_sistema) })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: usuario => {
          this.guardando.set(false);
          this.exito.set(`Usuario ${usuario.email} creado con rol ${usuario.roles.join(', ')}.`);
          this.form.reset();
          this.cargarUsuarios();
        },
        error: err => {
          this.guardando.set(false);
          this.mostrarError(err, 'No se pudo crear el usuario.');
        },
      });
  }

  eliminar(usuario: UsuarioAdmin): void {
    if (usuario.id_usuario === this.idUsuarioActual()) return;
    const confirmado = window.confirm(
      `¿Eliminar la cuenta de ${usuario.nombres} ${usuario.apellidos} (${usuario.email})? Esta acción no se puede deshacer.`,
    );
    if (!confirmado) return;

    this.limpiarMensajes();
    this.eliminandoId.set(usuario.id_usuario);
    this.usuariosService
      .eliminar(usuario.id_usuario)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.eliminandoId.set(null);
          this.exito.set(`Usuario ${usuario.email} eliminado.`);
          this.usuarios.update(lista => lista.filter(u => u.id_usuario !== usuario.id_usuario));
        },
        error: err => {
          this.eliminandoId.set(null);
          this.mostrarError(err, 'No se pudo eliminar el usuario.');
        },
      });
  }

  limpiarMensajes(): void {
    this.error.set(null);
    this.exito.set(null);
  }

  // Traduce el error del backend a un mensaje claro. Para 400/404/409 se
  // muestra el detalle que envía la API (ej: "Ya existe un usuario con ese correo").
  private mostrarError(err: HttpErrorResponse, porDefecto: string): void {
    const detalle = typeof err?.error?.detail === 'string' ? err.error.detail : null;
    if (err?.status === 401) {
      this.error.set('Tu sesión expiró. Iniciá sesión nuevamente.');
    } else if (err?.status === 403) {
      this.error.set('Solo el administrador puede gestionar usuarios.');
    } else if (detalle && [400, 404, 409].includes(err.status)) {
      this.error.set(detalle);
    } else if (err?.status === 422) {
      this.error.set('Revisá los datos: correo y cédula válidos, y contraseña de al menos 8 caracteres.');
    } else {
      this.error.set(porDefecto);
    }
  }
}
