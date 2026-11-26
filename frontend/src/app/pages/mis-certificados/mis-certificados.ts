import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { CertificadosService, MiCertificado } from '../../services/certificados';

export type EstadoMiCertificado = 'emitido' | 'disponible' | 'en_curso' | 'no_alcanza' | 'no_aplica';

// "Mis certificados": el participante ve sus inscripciones, su asistencia
// frente al mínimo de cada evento y descarga los certificados emitidos.
@Component({
  selector: 'app-mis-certificados',
  imports: [DatePipe, DecimalPipe, RouterLink],
  templateUrl: './mis-certificados.html',
  styleUrl: './mis-certificados.scss',
})
export class MisCertificados implements OnInit {
  private certificadosService = inject(CertificadosService);
  private destroyRef = inject(DestroyRef);

  certificados = signal<MiCertificado[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);
  descargandoId = signal<number | null>(null);

  emitidos = computed(() => this.certificados().filter(c => c.certificado_emitido).length);

  ngOnInit(): void {
    this.certificadosService
      .listarMios()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: lista => {
          this.certificados.set(lista);
          this.cargando.set(false);
        },
        error: err => {
          this.cargando.set(false);
          this.error.set(
            err?.status === 403
              ? 'Esta sección es para participantes.'
              : 'No se pudieron cargar tus certificados.',
          );
        },
      });
  }

  // Estado que se muestra en cada tarjeta, según emisión, inscripción y
  // asistencia registrada frente al mínimo del evento.
  estado(c: MiCertificado): EstadoMiCertificado {
    if (c.certificado_emitido) return 'emitido';
    if (c.estado_inscripcion !== 'confirmada') return 'no_aplica';
    if (c.elegible) return 'disponible';
    const hoy = new Date().toISOString().slice(0, 10);
    return c.fecha_fin_evento >= hoy ? 'en_curso' : 'no_alcanza';
  }

  textoEstado(c: MiCertificado): string {
    switch (this.estado(c)) {
      case 'emitido': return 'Emitido';
      case 'disponible': return 'Pendiente de emisión';
      case 'en_curso': return 'Evento en curso';
      case 'no_alcanza': return 'No alcanzó el mínimo';
      default: return c.estado_inscripcion === 'lista_de_espera' ? 'En lista de espera' : 'Sin certificado';
    }
  }

  detalleEstado(c: MiCertificado): string {
    switch (this.estado(c)) {
      case 'emitido': return 'Ya podés descargarlo o compartir su código de verificación.';
      case 'disponible': return 'Cumpliste la asistencia mínima. El organizador emitirá tu certificado.';
      case 'en_curso': return 'Tu asistencia se sigue registrando en cada actividad.';
      case 'no_alcanza': return 'Tu asistencia quedó por debajo del mínimo exigido por el evento.';
      default: return 'Solo las inscripciones confirmadas pueden recibir certificado.';
    }
  }

  descargar(c: MiCertificado): void {
    this.descargandoId.set(c.id_inscripcion);
    this.error.set(null);
    this.certificadosService
      .descargarMio(c.id_inscripcion)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: pdf => {
          this.descargandoId.set(null);
          const url = URL.createObjectURL(pdf);
          const enlace = document.createElement('a');
          enlace.href = url;
          enlace.download = `certificado-${c.codigo_validacion}.pdf`;
          enlace.click();
          setTimeout(() => URL.revokeObjectURL(url), 60_000);
        },
        error: () => {
          this.descargandoId.set(null);
          this.error.set(`No se pudo descargar el certificado de «${c.evento}».`);
        },
      });
  }
}
