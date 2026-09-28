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
      codigo: ['', [Validators.required, Validators.maxLength(50)]],
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

          this.stopLoading();
        },

        error: () => {
          this.rolesList.set([
            new RolParticipante({
              id_rol_participante: 1,
              codigo: 'EST',
              nombre: 'Estudiante',
              descripcion: 'Matriculado',
              activo: true,
              en_uso: true
            }),
            new RolParticipante({
              id_rol_participante: 2,
              codigo: 'EXP',
              nombre: 'Expositor',
              descripcion: 'Conferencista',
              activo: true,
              en_uso: false
            })
          ]);

          this.errorMessage =
            'No se pudo conectar con el servidor. Se muestran datos de respaldo.';

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

    const newRole = new RolParticipante({
      codigo: this.roleForm.value.codigo,
      nombre: this.roleForm.value.nombre,
      descripcion: this.roleForm.value.descripcion,
      activo: true,
      en_uso: false
    });

    this.rolesService
      .create(newRole)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (created) => {
          this.stopLoading();

          this.successMessage = 'Rol creado exitosamente.';

          this.rolesList.update(roles => [
            ...roles,
            new RolParticipante(created)
          ]);

          this.roleForm.reset();
        },

        error: () => {
          this.stopLoading();
          this.errorMessage = 'No se pudo registrar el rol.';
        }
      });
  }

  onDeleteRole(role: RolParticipante): void {
    this.clearMessages();

    if (role.en_uso) {
      this.errorMessage =
        `No se puede eliminar el rol "${role.nombre}" porque actualmente se encuentra asignado a inscripciones activas.`;
      return;
    }

    if (role.id_rol_participante) {
      this.rolesService
        .delete(role.id_rol_participante)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.rolesList.update(
              roles =>
                roles.filter(
                  r => r.id_rol_participante !== role.id_rol_participante
                )
            );

            this.successMessage = 'Rol eliminado correctamente.';
          },

          error: () => {
            this.errorMessage = 'No se pudo eliminar el rol.';
          }
        });
    }
  }
}
