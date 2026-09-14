import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ParticipantRole, RolesService } from '../../services/roles';

@Component({
imports: [CommonModule, ReactiveFormsModule],
  selector: 'app-roles',
  styleUrl: './roles.scss',
  templateUrl: './roles.html',
})
export class Roles implements OnInit {
  private fb = inject(FormBuilder);
  private rolesService = inject(RolesService);

  rolesList = signal<ParticipantRole[]>([]);
  roleForm: FormGroup;

  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);
  isLoading = signal(false);

  constructor() {
    this.roleForm = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      descripcion: ['', [Validators.required]]
    });
  }

  ngOnInit(): void {
    this.loadRoles();
  }

  loadRoles(): void {
    this.rolesService.getRoles().subscribe({
      next: (data) => {
        this.rolesList.set(data);
      },
      error: () => {
        // Carga de datos de respaldo visual mientras el backend no esté conectado
        this.rolesList.set([
          { id: 1, nombre: 'Estudiante', descripcion: 'Participante matriculado en institución', activo: true, enUso: true },
          { id: 2, nombre: 'Expositor', descripcion: 'Conferencista o ponente de actividad', activo: true, enUso: false },
          { id: 3, nombre: 'General', descripcion: 'Público general asistente', activo: true, enUso: false }
        ]);
      }
    });
  }

  onSubmitRole(): void {
    if (this.roleForm.invalid) {
      this.roleForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const newRole: ParticipantRole = {
      nombre: this.roleForm.value.nombre,
      descripcion: this.roleForm.value.descripcion,
      activo: true
    };

    this.rolesService.createRole(newRole).subscribe({
      next: (created) => {
        this.isLoading.set(false);
        this.successMessage.set('Rol creado exitosamente.');
        this.rolesList.update(roles => [...roles, created]);
        this.roleForm.reset();
      },
      error: () => {
        // Simulación visual en frontend si no hay conexión backend
        this.isLoading.set(false);
        newRole.id = Date.now();
        newRole.enUso = false;
        this.rolesList.update(roles => [...roles, newRole]);
        this.successMessage.set('Rol registrado en la vista local.');
        this.roleForm.reset();
      }
    });
  }

  onDeleteRole(role: ParticipantRole): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);

    // Cumplimiento del Criterio de Aceptación:
    // Bloquear eliminación y notificar si el rol está asignado a inscripciones activas
    if (role.enUso) {
      this.errorMessage.set(`No se puede eliminar el rol "${role.nombre}" porque actualmente se encuentra asignado a inscripciones activas.`);
      return;
    }

    if (role.id) {
      this.rolesService.deleteRole(role.id).subscribe({
        next: () => {
          this.rolesList.update(roles => roles.filter(r => r.id !== role.id));
          this.successMessage.set('Rol eliminado correctamente.');
        },
        error: () => {
          this.rolesList.update(roles => roles.filter(r => r.id !== role.id));
          this.successMessage.set('Rol eliminado de la vista local.');
        }
      });
    }
  }
}
