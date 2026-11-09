import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { Evento, EventosService } from '../../services/eventos';
import {
  InscripcionResultado,
  InscripcionesService,
  RolParticipantePublico,
} from '../../services/inscripciones';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-inscripcion-publica',
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './inscripcion-publica.html',
  styleUrl: './inscripcion-publica.scss',
})
export class InscripcionPublica implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private eventosService = inject(EventosService);
  private inscripcionesService = inject(InscripcionesService);
  private auth = inject(AuthService);

  // Con sesión vuelve a la pantalla principal; sin sesión, al login.
  rutaInicio = this.auth.isLoggedIn() ? '/inicio' : '/login';
  textoInicio = this.auth.isLoggedIn() ? 'Volver al inicio' : 'Iniciar sesión';

  eventos = signal<Evento[]>([]);
  roles = signal<RolParticipantePublico[]>([]);
  cargando = signal(true);
  enviando = signal(false);
  error = signal<string | null>(null);
  resultado = signal<InscripcionResultado | null>(null);

  form = this.fb.nonNullable.group({
    id_evento: [0, [Validators.required, Validators.min(1)]],
    id_rol_participante: [0, [Validators.required, Validators.min(1)]],
    documento: [''],
    nombres: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    apellidos: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email]],
    institucion: [''],
  });

  ngOnInit(): void {
    const eventoRuta = Number(this.route.snapshot.paramMap.get('id')) || 0;

    forkJoin({
      eventos: this.eventosService.getEventos({ estado: 'publicado' }),
      roles: this.inscripcionesService.getRolesPublicos(),
    })
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: ({ eventos, roles }) => {
          this.eventos.set(eventos);
          this.roles.set(roles);

          const eventoSeleccionado = eventos.some(e => e.id_evento === eventoRuta)
            ? eventoRuta
            : (eventos[0]?.id_evento ?? 0);

          const rolAsistente =
            roles.find(r => r.nombre.toLocaleLowerCase().includes('asistente'))
              ?.id_rol_participante ?? roles[0]?.id_rol_participante ?? 0;

          this.form.patchValue({
            id_evento: eventoSeleccionado,
            id_rol_participante: rolAsistente,
          });
        },
        error: () => {
          this.error.set('No fue posible cargar los datos necesarios para la inscripción.');
        },
      });
  }

  enviar(): void {
    this.error.set(null);
    this.resultado.set(null);

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Revisá los campos obligatorios antes de continuar.');
      return;
    }

    const value = this.form.getRawValue();
    this.enviando.set(true);

    this.inscripcionesService.inscribir({
      id_evento: Number(value.id_evento),
      id_rol_participante: Number(value.id_rol_participante),
      documento: value.documento.trim() || null,
      nombres: value.nombres.trim(),
      apellidos: value.apellidos.trim(),
      email: value.email.trim(),
      institucion: value.institucion.trim() || null,
    })
      .pipe(finalize(() => this.enviando.set(false)))
      .subscribe({
        next: data => this.resultado.set(data),
        error: err => {
          this.error.set(
            err?.error?.detail || 'No fue posible completar la inscripción.'
          );
        },
      });
  }

  nombreEvento(): string {
    const id = Number(this.form.controls.id_evento.value);
    return this.eventos().find(e => e.id_evento === id)?.nombre ?? 'Evento';
  }

  nuevaInscripcion(): void {
    const evento = this.form.controls.id_evento.value;
    const rol = this.form.controls.id_rol_participante.value;
    this.form.reset({
      id_evento: evento,
      id_rol_participante: rol,
      documento: '',
      nombres: '',
      apellidos: '',
      email: '',
      institucion: '',
    });
    this.resultado.set(null);
    this.error.set(null);
  }
}
