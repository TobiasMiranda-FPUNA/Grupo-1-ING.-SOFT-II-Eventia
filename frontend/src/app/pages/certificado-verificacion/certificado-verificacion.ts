import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import {
  CertificadoVerificado,
  CertificadosService,
} from '../../services/certificados';

@Component({
  selector: 'app-certificado-verificacion',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './certificado-verificacion.html',
  styleUrl: './certificado-verificacion.scss',
})
export class CertificadoVerificacion implements OnInit {
  private route = inject(ActivatedRoute);
  private certificadosService = inject(CertificadosService);

  codigo = '';
  buscando = signal(false);
  error = signal<string | null>(null);
  certificado = signal<CertificadoVerificado | null>(null);

  ngOnInit(): void {
    const codigoRuta = this.route.snapshot.paramMap.get('codigo');
    if (codigoRuta) {
      this.codigo = codigoRuta;
      this.verificar();
    }
  }

  verificar(): void {
    const codigo = this.codigo.trim();
    this.error.set(null);
    this.certificado.set(null);

    if (!codigo) {
      this.error.set('Ingresá el código de validación del certificado.');
      return;
    }

    this.buscando.set(true);
    this.certificadosService.verificar(codigo)
      .pipe(finalize(() => this.buscando.set(false)))
      .subscribe({
        next: data => this.certificado.set(data),
        error: err => this.error.set(
          err?.error?.detail || 'No se encontró un certificado válido con ese código.'
        ),
      });
  }

  descargar(): void {
    const certificado = this.certificado();
    if (!certificado) return;

    const html = `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Certificado - ${this.escape(certificado.participante)}</title>
<style>
body{font-family:Arial,sans-serif;margin:0;padding:40px;background:#f1f5f9;color:#0f172a}
.cert{max-width:900px;margin:auto;background:#fff;border:10px solid #e2e8f0;padding:70px;text-align:center}
.brand{font-weight:800;letter-spacing:.2em;color:#2563eb}.title{font-size:40px;margin:28px 0 14px}.name{font-size:30px;font-weight:800;margin:20px 0}.event{font-size:22px}.code{margin-top:48px;font-family:monospace;font-size:14px;color:#475569}.date{margin-top:20px;color:#64748b}
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
