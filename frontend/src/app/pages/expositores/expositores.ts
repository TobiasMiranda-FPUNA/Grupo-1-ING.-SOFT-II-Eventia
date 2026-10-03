
import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';

import { forkJoin, from, of } from 'rxjs';
import { catchError, concatMap, toArray } from 'rxjs/operators';

import {
  Conferencista,
  ConferencistasService
} from '../../services/conferencistas';

import {
  Actividad,
  ActividadesService
} from '../../services/actividades';

import { EventosService } from '../../services/eventos';

interface ActividadConConferencistas extends Actividad {
  conferencistas?: Conferencista[];
}

interface ExpositorVista extends Conferencista {
  actividades: Actividad[];
}

@Component({
  selector: 'app-expositores',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './expositores.html',
  styleUrl: './expositores.scss'
})
export class Expositores implements OnInit {
  private fb = inject(FormBuilder);
  private conferencistasService = inject(ConferencistasService);
  private actividadesService = inject(ActividadesService);
  private eventosService = inject(EventosService);

  expositores = signal<ExpositorVista[]>([]);
  actividades = signal<Actividad[]>([]);
  busqueda = signal('');

  expositoresFiltrados = computed(() => {
    const termino = this.busqueda().trim().toLocaleLowerCase();

    if (!termino) return this.expositores();

    return this.expositores().filter(e =>
      `${e.nombres} ${e.apellidos}`.toLocaleLowerCase().includes(termino) ||
      (e.especialidad ?? '').toLocaleLowerCase().includes(termino)
    );
  });

  expositoresForm: FormGroup;

  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);
  isLoading = signal(false);

  constructor() {
    this.expositoresForm = this.fb.group({
      nombres: ['', [Validators.required, Validators.minLength(2)]],
      apellidos: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      institucion: [''],
      especialidad: [''],
      biografia: [''],
      actividades: [[] as number[]]
    });
  }

  ngOnInit(): void {
    this.loadExpositores();
  }

  onBuscar(event: Event): void {
    this.busqueda.set((event.target as HTMLInputElement).value);
  }

  onActividadesChange(event: Event): void {
    const select = event.target as HTMLSelectElement;

    this.expositoresForm.patchValue({
      actividades: Array.from(select.selectedOptions).map(
        option => Number(option.value)
      )
    });
  }

  iniciales(expositor: Conferencista): string {
    const iniciales =
      `${expositor.nombres?.trim().charAt(0) ?? ''}${expositor.apellidos?.trim().charAt(0) ?? ''}`;

    return iniciales.toLocaleUpperCase() || 'EX';
  }

  fechaActividad(fecha: string): string {
    if (!fecha) return 'Fecha no disponible';

    const [anio, mes, dia] = fecha.slice(0, 10).split('-').map(Number);

    if (!anio || !mes || !dia) return fecha;

    return new Intl.DateTimeFormat('es-PY', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(new Date(anio, mes - 1, dia));
  }

  loadExpositores(): void {
    this.isLoading.set(true);

    this.conferencistasService.getConferencistas().subscribe({
      next: data => this.loadActividadesYRelaciones(data),
      error: error => {
        this.isLoading.set(false);
        this.showHttpError(
          error,
          'No fue posible cargar los expositores.'
        );
      }
    });
  }

  private loadActividadesYRelaciones(
    conferencistas: Conferencista[]
  ): void {
    this.eventosService.getEventos().subscribe({
      next: eventos => {
        if (!eventos.length) {
          this.actividades.set([]);

          this.expositores.set(
            conferencistas.map(e => ({
              ...e,
              actividades: []
            }))
          );

          this.isLoading.set(false);
          return;
        }

        const consultas = eventos.map(evento =>
          this.actividadesService
            .getActividadesPorEvento(evento.id_evento)
            .pipe(catchError(() => of([] as Actividad[])))
        );

        forkJoin(consultas).subscribe({
          next: resultados => {
            const todas = resultados.flat() as ActividadConConferencistas[];

            this.actividades.set(todas);

            this.expositores.set(
              conferencistas.map(e => ({
                ...e,
                actividades: todas.filter(actividad =>
                  actividad.conferencistas?.some(
                    conferencista =>
                      conferencista.id_conferencista === e.id_conferencista
                  )
                )
              }))
            );

            this.isLoading.set(false);
          },
          error: () => {
            this.errorMessage.set(
              'No fue posible cargar las actividades de los eventos.'
            );

            this.expositores.set(
              conferencistas.map(e => ({
                ...e,
                actividades: []
              }))
            );

            this.isLoading.set(false);
          }
        });
      },
      error: () => {
        this.errorMessage.set(
          'No fue posible obtener los eventos para cargar las actividades.'
        );

        this.expositores.set(
          conferencistas.map(e => ({
            ...e,
            actividades: []
          }))
        );

        this.isLoading.set(false);
      }
    });
  }

  onSubmit(): void {
    if (this.expositoresForm.invalid) {
      this.expositoresForm.markAllAsTouched();

      this.errorMessage.set(
        'Revisá los campos obligatorios antes de continuar.'
      );

      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const values = this.expositoresForm.getRawValue();

    const nuevoExpositor: Conferencista = {
      nombres: values.nombres,
      apellidos: values.apellidos,
      email: values.email,
      institucion: values.institucion || undefined,
      especialidad: values.especialidad || undefined,
      biografia: values.biografia || undefined
    };

    // Normalizar las actividades seleccionadas como números.
    const actividadesSeleccionadas: unknown[] =
      Array.isArray(values.actividades)
        ? values.actividades
        : [];

    // Eliminar IDs repetidos y conservar únicamente valores numéricos válidos.
    const seleccionadas: number[] = Array.from(
      new Set<number>(
        actividadesSeleccionadas
          .map(id => Number(id))
          .filter(id => Number.isInteger(id) && id > 0)
      )
    );

    this.conferencistasService
      .createConferencista(nuevoExpositor)
      .subscribe({
        next: creado => {
          const conferencistaId = creado.id_conferencista;

          if (!conferencistaId) {
            this.isLoading.set(false);

            this.errorMessage.set(
              'El expositor fue creado, pero no se pudo obtener su identificador.'
            );

            this.loadExpositores();
            return;
          }

          if (!seleccionadas.length) {
            this.finalizarCreacion(false);
            return;
          }

          // Procesar las asociaciones secuencialmente.
          const solicitudes = from(seleccionadas).pipe(
            concatMap(actividadId =>
              this.actividadesService.asociarConferencista(
                actividadId,
                conferencistaId
              )
            ),
            toArray()
          );

          solicitudes.subscribe({
            next: () => {
              this.finalizarCreacion(true);
            },
            error: error => {
              this.isLoading.set(false);

              this.showHttpError(
                error,
                'El expositor fue creado, pero no se pudieron asignar todas las actividades.'
              );

              this.resetFormulario();
              this.loadExpositores();
            }
          });
        },
        error: error => {
          this.isLoading.set(false);

          this.showHttpError(
            error,
            'No fue posible registrar el expositor.'
          );
        }
      });
  }

  private finalizarCreacion(tieneActividades: boolean): void {
    this.successMessage.set(
      tieneActividades
        ? 'Expositor registrado y asociado correctamente a las actividades seleccionadas.'
        : 'Expositor registrado correctamente.'
    );

    this.resetFormulario();
    this.loadExpositores();
  }

  private resetFormulario(): void {
    this.expositoresForm.reset({
      nombres: '',
      apellidos: '',
      email: '',
      institucion: '',
      especialidad: '',
      biografia: '',
      actividades: []
    });
  }

  private showHttpError(error: any, defaultMessage: string): void {
    switch (error?.status) {
      case 400:
        this.errorMessage.set(
          'Los datos enviados no son válidos. Revisá la información ingresada.'
        );
        break;

      case 401:
        this.errorMessage.set(
          'Tu sesión expiró. Iniciá sesión nuevamente.'
        );
        break;

      case 403:
        this.errorMessage.set(
          'No tenés permisos para realizar esta operación.'
        );
        break;

      case 404:
        this.errorMessage.set(
          'No se encontró el recurso solicitado.'
        );
        break;

      case 409:
        this.errorMessage.set(
          'Ya existe un expositor registrado con ese correo electrónico o la asociación ya existe.'
        );
        break;

      case 422:
        this.errorMessage.set(
          'Los datos ingresados no cumplen con las validaciones requeridas.'
        );
        break;

      default:
        this.errorMessage.set(defaultMessage);
        break;
    }
  }

  onDelete(expositor: Conferencista): void {
    if (!expositor.id_conferencista) return;

    const nombre =
      `${expositor.nombres} ${expositor.apellidos}`.trim();

    if (!window.confirm(`¿Estás seguro de eliminar a ${nombre}?`)) {
      return;
    }

    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.conferencistasService
      .deleteConferencista(expositor.id_conferencista)
      .subscribe({
        next: () => {
          this.successMessage.set(
            'Expositor eliminado correctamente.'
          );

          this.loadExpositores();
        },
        error: error =>
          this.showHttpError(
            error,
            'No fue posible eliminar el expositor.'
          )
      });
  }
}
