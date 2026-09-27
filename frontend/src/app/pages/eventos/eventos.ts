import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Evento, EventosService, TipoEvento } from '../../services/eventos';

@Component({
  selector: 'app-eventos',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './eventos.html',
  styleUrl: './eventos.scss',
})
export class Eventos implements OnInit {
  private eventosService = inject(EventosService);

  eventos = signal<Evento[]>([]);
  tipos = signal<TipoEvento[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);

  busqueda = '';
  estado = '';
  tipo = '';
  vista: 'grilla' | 'lista' = 'grilla';

  ngOnInit(): void {
    this.cargarTipos();
    this.cargarEventos();
  }

  cargarTipos(): void {
    this.eventosService.getTiposEvento().subscribe({
      next: data => this.tipos.set(data.filter(t => t.activo)),
      error: () => this.tipos.set([]),
    });
  }

  cargarEventos(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.eventosService.getEventos({
      q: this.busqueda.trim() || undefined,
      estado: this.estado || undefined,
      id_tipo_evento: this.tipo ? Number(this.tipo) : undefined,
    }).subscribe({
      next: data => {
        this.eventos.set(data);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el catálogo de eventos.');
        this.cargando.set(false);
      },
    });
  }

  limpiarFiltros(): void {
    this.busqueda = '';
    this.estado = '';
    this.tipo = '';
    this.cargarEventos();
  }

  nombreTipo(id: number): string {
    return this.tipos().find(t => t.id_tipo_evento === id)?.nombre ?? `Tipo #${id}`;
  }
}
