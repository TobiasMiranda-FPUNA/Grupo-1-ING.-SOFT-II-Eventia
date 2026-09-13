import { Component, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../services/auth';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  imports: [CommonModule, ReactiveFormsModule],
  selector: 'app-login',
  styleUrl: './login.scss',
  templateUrl: './login.html',
})
export class Login {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  isLoading = signal(false);
  showInvalidCredentialsAlert = signal(false);

  loginForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);

    const credentials = {
      email: this.loginForm.value.email,
      password: this.loginForm.value.password
    };

    this.authService.login(credentials).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/roles']);
      },
      error: () => {
        this.isLoading.set(false);
        // Cumple el Criterio de Aceptación: error claro sin revelar si falló correo o clave
        this.showInvalidCredentialsAlert.set(true);
      }
    });
  }

  closeInvalidCredentialsAlert(): void {
    this.showInvalidCredentialsAlert.set(false);
    this.loginForm.reset();
    this.loginForm.markAsPristine();
    this.loginForm.markAsUntouched();
  }
}
