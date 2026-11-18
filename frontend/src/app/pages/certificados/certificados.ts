import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import {
  CertificadoGestion,
  CertificadoVerificado,
  CertificadosService,
  EnvioCorreo,
} from '../../services/certificados';
import { Evento, EventosService } from '../../services/eventos';

@Component({
  selector: 'app-certificados',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './certificados.html',
  styleUrl: './certificados.scss',
})
export class Certificados implements OnInit {
  private eventosService = inject(EventosService);
  private certificadosService = inject(CertificadosService);

  eventos = signal<Evento[]>([]);
  participantes = signal<CertificadoGestion[]>([]);

  eventoId: number | null = null;
  cargando = signal(false);
  procesando = signal<number | null>(null);
  enviandoTodos = signal(false);
  mensaje = signal<string | null>(null);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.eventosService.getEventos().subscribe({
      next: eventos => this.eventos.set(eventos),
      error: () => this.error.set('No se pudieron cargar los eventos.'),
    });
  }

  // conservarMensajes: recarga la lista sin borrar el resultado de la última acción.
  cargar(conservarMensajes = false): void {
    this.participantes.set([]);
    if (!conservarMensajes) {
      this.mensaje.set(null);
      this.error.set(null);
    }

    if (!this.eventoId) return;

    this.cargando.set(true);
    this.certificadosService
      .listarPorEvento(this.eventoId)
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: participantes => this.participantes.set(participantes),
        error: err => this.error.set(
          err?.error?.detail || 'No se pudo consultar el estado de certificados.'
        ),
      });
  }

  emitir(item: CertificadoGestion): void {
    this.procesando.set(item.id_inscripcion);
    this.error.set(null);
    this.mensaje.set(null);

    this.certificadosService
      .emitir(item.id_inscripcion)
      .pipe(finalize(() => this.procesando.set(null)))
      .subscribe({
        next: certificado => {
          this.informarEnvio(
            `Certificado generado para ${certificado.participante}`,
            certificado.envio_correo,
            certificado.email,
          );
          this.cargar(true);
        },
        error: err => this.error.set(
          err?.error?.detail || 'No se pudo generar el certificado.'
        ),
      });
  }

  reenviar(item: CertificadoGestion): void {
    this.procesando.set(item.id_inscripcion);
    this.error.set(null);
    this.mensaje.set(null);

    this.certificadosService
      .reenviar(item.id_inscripcion)
      .pipe(finalize(() => this.procesando.set(null)))
      .subscribe({
        next: certificado => this.mensaje.set(`Certificado reenviado a ${certificado.email}.`),
        error: err => this.error.set(
          err?.error?.detail || 'No se pudo reenviar el certificado.'
        ),
      });
  }

  // Emite y envía por correo los certificados de todos los que culminaron el evento.
  emitirYEnviarTodos(): void {
    if (!this.eventoId) return;

    this.enviandoTodos.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.certificadosService
      .emitirYEnviarEvento(this.eventoId)
      .pipe(finalize(() => this.enviandoTodos.set(false)))
      .subscribe({
        next: r => {
          if (r.emitidos === 0) {
            this.mensaje.set('No hay participantes elegibles con certificado pendiente.');
          } else {
            const partes = [`${r.emitidos} certificado(s) emitido(s)`, `${r.enviados} enviado(s) por correo`];
            if (r.con_error) partes.push(`${r.con_error} con error de envío`);
            this.mensaje.set(partes.join(' · ') + '.');
            if (r.sin_configurar) {
              this.error.set('El envío de correos no está configurado en el servidor: los certificados se emitieron pero no se enviaron.');
            }
          }
          this.cargar(true);
        },
        error: err => this.error.set(
          err?.error?.detail || 'No se pudieron emitir y enviar los certificados.'
        ),
      });
  }

  hayPendientes(): boolean {
    return this.participantes().some(p => p.elegible && !p.certificado_emitido);
  }

  private informarEnvio(prefijo: string, envio: EnvioCorreo | null | undefined, email: string): void {
    if (envio === 'enviado') {
      this.mensaje.set(`${prefijo} y enviado a ${email}.`);
    } else if (envio === 'error') {
      this.mensaje.set(`${prefijo}.`);
      this.error.set(`No se pudo enviar el correo a ${email}. Podés reintentar con "Reenviar".`);
    } else {
      this.mensaje.set(`${prefijo}.`);
      if (envio === 'no_configurado') {
        this.error.set('El envío de correos no está configurado en el servidor (SMTP).');
      }
    }
  }

  descargar(item: CertificadoGestion): void {
    if (!item.codigo_validacion) return;

    this.certificadosService.verificar(item.codigo_validacion).subscribe({
      next: cert => this.descargarHtml(cert),
      error: () => this.error.set('No se pudo obtener el certificado para descargar.'),
    });
  }

  private descargarHtml(certificado: CertificadoVerificado): void {
    const html = `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Certificado - ${this.escape(certificado.participante)}</title>
<style>
@page{size:A4 landscape;margin:0}body{font-family:Arial,sans-serif;margin:0;background:#eef2f7;color:#0f172a}
.cert{box-sizing:border-box;width:297mm;height:210mm;margin:auto;background:white;border:12px solid #dbeafe;padding:38mm 30mm;text-align:center}
.brand{font-weight:900;letter-spacing:.28em;color:#2563eb}.title{font-size:38px;margin:24px 0 12px}.name{font-size:31px;font-weight:800;margin:18px 0}.event{font-size:22px}.code{margin-top:34px;font-family:monospace;font-size:13px;color:#475569}.date{margin-top:18px;color:#64748b}
</style></head><body><div class="cert"><div class="brand">EVENTIA</div><div class="title">Certificado de ${this.escape(certificado.tipo)}</div><p>Se certifica la participación de</p><div class="name">${this.escape(certificado.participante)}</div><p>en el evento</p><div class="event">${this.escape(certificado.evento)}</div><div class="date">Emitido: ${new Date(certificado.fecha_emision).toLocaleDateString('es-PY')}</div><div class="code">Código de validación: ${this.escape(certificado.codigo_validacion)}</div></div></body></html>`;

    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `certificado_${certificado.codigo_validacion}.html`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  private escape(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }
}
