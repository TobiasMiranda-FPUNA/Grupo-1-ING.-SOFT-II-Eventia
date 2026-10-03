import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { RolesService } from '../../services/roles-service';
import { BaseComponent } from '../../core/base.component';
import { RolParticipante } from '../../models/rol-participante.model';

@Component({
  selector: 'app-roles',
  imports: [CommonModule, ReactiveFormsModule],
  styleUrl: './roles.scss',
  templateUrl: './roles.html',
})
export class Roles extends BaseComponent implements OnInit {

  private fb = inject(FormBuilder);
  private rolesService = inject(RolesService);
  private destroyRef = inject(DestroyRef);

  rolesList = signal<RolParticipante[]>([]);

  roleForm: FormGroup;

  constructor() {
    super();

    this.roleForm = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      descripcion: ['', [Validators.required]]
    });
  }

  ngOnInit(): void {
    this.loadRoles();
  }

  loadRoles(): void {
    this.startLoading();

    this.rolesService
      .getAll()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.rolesList.set(
            data.map(rol => new RolParticipante(rol))
          );

          this.errorMessage = '';
          this.stopLoading();
        },

        error: (error) => {
          this.rolesList.set([]);

          this.errorMessage =
            error.status === 401
              ? 'Tu sesión no es válida. Iniciá sesión nuevamente.'
              : error.status === 403
                ? 'No tenés permisos para consultar los roles.'
                : 'No se pudieron cargar los roles desde el servidor.';

          this.stopLoading();
        }
      });
  }

  onSubmitRole(): void {
    if (this.roleForm.invalid) {
      this.roleForm.markAllAsTouched();
      return;
    }

    this.startLoading();

    const newRole = {
      nombre: this.roleForm.value.nombre,
      descripcion: this.roleForm.value.descripcion
    };

    this.rolesService
      .create(newRole as RolParticipante)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.stopLoading();

          this.successMessage = 'Rol creado exitosamente.';
          this.roleForm.reset();

          this.loadRoles();
        },

        error: (error) => {
          this.stopLoading();

          this.errorMessage =
            error.status === 409
              ? 'Ya existe un rol con ese nombre.'
              : error.status === 401
                ? 'Tu sesión expiró. Iniciá sesión nuevamente.'
                : error.status === 403
                  ? 'No tenés permisos para crear roles.'
                  : 'No se pudo registrar el rol.';
        }
      });
  }

  onDeleteRole(role: RolParticipante): void {
    this.clearMessages();

    if (role.id === undefined) {
      this.errorMessage = 'No se encontró el identificador del rol.';
      return;
    }

    this.rolesService
      .delete(role.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.successMessage = 'Rol eliminado correctamente.';
          this.loadRoles();
        },

        error: (error) => {
          this.errorMessage =
            error.status === 409
              ? 'No se puede eliminar el rol porque está siendo utilizado.'
              : error.status === 401
                ? 'Tu sesión expiró. Iniciá sesión nuevamente.'
                : error.status === 403
                  ? 'No tenés permisos para eliminar roles.'
                  : 'No se pudo eliminar el rol.';
        }
      });
  }
}