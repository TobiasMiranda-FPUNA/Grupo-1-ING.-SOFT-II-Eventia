import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EventoPayload, EventosService, TipoEvento } from '../../services/eventos';

@Component({
  selector: 'app-evento-form',
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './evento-form.html',
  styleUrl: './evento-form.scss',
})
export class EventoForm implements OnInit {
  private fb = inject(FormBuilder);
  private service = inject(EventosService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  paso = signal(1);
  tipos = signal<TipoEvento[]>([]);
  guardando = signal(false);
  cargando = signal(false);
  error = signal<string | null>(null);
  eventoId: number | null = null;

  form = this.fb.group({
    id_tipo_evento: ['', Validators.required],
    nombre: ['', [Validators.required, Validators.maxLength(150)]],
    descripcion: ['', Validators.maxLength(500)],
    fecha_inicio: ['', Validators.required],
    fecha_fin: ['', Validators.required],
    lugar: [''],
    cupo_maximo: [1, [Validators.required, Validators.min(1)]],
    estado: ['borrador', Validators.required],
    fecha_limite: [''],
    requiere_aprobacion: [false],
    permite_lista_espera: [false],
    min_asistencia_certificado: [75, [Validators.required, Validators.min(0), Validators.max(100)]],
  });

  get esEdicion(): boolean { return this.eventoId !== null; }

  ngOnInit(): void {
    this.cargarTipos();
    const rawId = this.route.snapshot.paramMap.get('id');
    if (rawId) {
      this.eventoId = Number(rawId);
      this.cargarEvento(this.eventoId);
    }
  }

  cargarTipos(): void {
    this.service.getTiposEvento().subscribe({
      next: data => this.tipos.set(data.filter(t => t.activo)),
      error: () => this.error.set('No se pudieron cargar los tipos de evento.'),
    });
  }

  cargarEvento(id: number): void {
    this.cargando.set(true);
    this.service.getEvento(id).subscribe({
      next: e => {
        this.form.patchValue({
          id_tipo_evento: String(e.id_tipo_evento), nombre: e.nombre, descripcion: e.descripcion ?? '',
          fecha_inicio: e.fecha_inicio, fecha_fin: e.fecha_fin, lugar: e.lugar ?? '',
          cupo_maximo: e.cupo_maximo, estado: e.estado,
          fecha_limite: e.politica?.fecha_limite ?? '',
          requiere_aprobacion: e.politica?.requiere_aprobacion ?? false,
          permite_lista_espera: e.politica?.permite_lista_espera ?? false,
          min_asistencia_certificado: e.politica?.min_asistencia_certificado ?? 75,
        });
        this.cargando.set(false);
      },
      error: () => { this.error.set('No se pudo cargar el evento.'); this.cargando.set(false); },
    });
  }

  siguiente(): void {
    this.error.set(null);
    if (this.paso() === 1) {
      const names = ['id_tipo_evento','nombre','fecha_inicio','fecha_fin','cupo_maximo'];
      names.forEach(n => this.form.get(n)?.markAsTouched());
      if (names.some(n => this.form.get(n)?.invalid)) return;
      const inicio = this.form.value.fecha_inicio!;
      const fin = this.form.value.fecha_fin!;
      if (fin < inicio) { this.error.set('La fecha de fin no puede ser anterior a la fecha de inicio.'); return; }
    }
    if (this.paso() < 3) this.paso.update(v => v + 1);
  }

  anterior(): void { if (this.paso() > 1) this.paso.update(v => v - 1); }

  guardar(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); this.error.set('Revisá los campos obligatorios.'); return; }
    const v = this.form.getRawValue();
    if (v.fecha_fin! < v.fecha_inicio!) { this.error.set('La fecha de fin no puede ser anterior a la fecha de inicio.'); this.paso.set(1); return; }

    const payload: EventoPayload = {
      id_tipo_evento: Number(v.id_tipo_evento), nombre: v.nombre!.trim(), descripcion: v.descripcion?.trim() || null,
      fecha_inicio: v.fecha_inicio!, fecha_fin: v.fecha_fin!, lugar: v.lugar?.trim() || null,
      cupo_maximo: Number(v.cupo_maximo), estado: v.estado as 'borrador' | 'publicado',
      politica: {
        fecha_limite: v.fecha_limite || null,
        requiere_aprobacion: !!v.requiere_aprobacion,
        permite_lista_espera: !!v.permite_lista_espera,
        min_asistencia_certificado: Number(v.min_asistencia_certificado),
      }
    };

    this.guardando.set(true); this.error.set(null);
    const request = this.eventoId ? this.service.updateEvento(this.eventoId, payload) : this.service.createEvento(payload);
    request.subscribe({
      next: () => this.router.navigate(['/eventos']),
      error: err => { this.guardando.set(false); this.error.set(err?.error?.detail || 'No se pudo guardar el evento.'); }
    });
  }

  nombreTipoSeleccionado(): string {
    const id = Number(this.form.value.id_tipo_evento);
    return this.tipos().find(t => t.id_tipo_evento === id)?.nombre ?? '-';
  }
}
