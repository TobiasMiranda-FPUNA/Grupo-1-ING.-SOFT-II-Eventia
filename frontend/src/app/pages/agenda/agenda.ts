import { CommonModule } from '@angular/common';
import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

type TipoActividad = 'Conferencia' | 'Taller' | 'Panel' | 'Networking';
interface Actividad {
  id: number;
  dia: number;
  inicio: number;
  fin: number;
  sala: string;
  titulo: string;
  tipo: TipoActividad;
  expositor: string;
  descripcion: string;
}

@Component({
  selector: 'app-agenda',
  imports: [CommonModule, FormsModule],
  templateUrl: './agenda.html',
  styleUrl: './agenda.scss',
})
export class Agenda {
  readonly dias = ['Martes 10 de junio', 'Miércoles 11 de junio', 'Jueves 12 de junio'];
  readonly salas = ['Sala A', 'Sala B', 'Sala C', 'Sala D'];
  readonly horas = Array.from({ length: 10 }, (_, i) => i + 8);

  diaSeleccionado = signal(0);
  salaFiltro = signal('Todas');
  tipoFiltro = signal('Todos');
  busqueda = signal('');
  actividadSeleccionada = signal<number | null>(2);
  agendaPersonal = signal<number[]>([]);
  esOrganizador = signal(false);

  readonly actividades: Actividad[] = [
    { id: 1, dia: 0, inicio: 8, fin: 9, sala: 'Sala A', titulo: 'Apertura del evento', tipo: 'Conferencia', expositor: 'Comité organizador', descripcion: 'Bienvenida e introducción a las actividades del congreso.' },
    { id: 2, dia: 0, inicio: 9, fin: 10, sala: 'Sala A', titulo: 'El futuro de la IA', tipo: 'Conferencia', expositor: 'Dra. Laura Méndez', descripcion: 'Exploraremos tendencias actuales y futuras de la inteligencia artificial y su impacto en la sociedad, la industria y la educación.' },
    { id: 3, dia: 0, inicio: 9, fin: 11, sala: 'Sala B', titulo: 'Taller: Introducción a Machine Learning', tipo: 'Taller', expositor: 'Ing. Carlos Benítez', descripcion: 'Introducción práctica a conceptos fundamentales de aprendizaje automático.' },
    { id: 4, dia: 0, inicio: 10, fin: 11, sala: 'Sala C', titulo: 'Panel: Innovación en Latinoamérica', tipo: 'Panel', expositor: 'Panel de invitados', descripcion: 'Experiencias y desafíos de innovación y transformación digital en la región.' },
    { id: 5, dia: 0, inicio: 11, fin: 12, sala: 'Sala A', titulo: 'Tecnología y sociedad', tipo: 'Conferencia', expositor: 'Prof. Ana Rojas', descripcion: 'Conversatorio sobre el impacto social de la tecnología.' },
    { id: 6, dia: 0, inicio: 11, fin: 12, sala: 'Sala D', titulo: 'Espacio de networking', tipo: 'Networking', expositor: 'Comunidad Eventia', descripcion: 'Espacio para conectar con otros asistentes.' },
    { id: 7, dia: 0, inicio: 14, fin: 15, sala: 'Sala A', titulo: 'Ciberseguridad en la nube', tipo: 'Conferencia', expositor: 'Lic. Diego Vera', descripcion: 'Buenas prácticas para proteger servicios y datos en la nube.' },
    { id: 8, dia: 0, inicio: 14, fin: 16, sala: 'Sala B', titulo: 'Taller: Desarrollo con Angular', tipo: 'Taller', expositor: 'Equipo frontend', descripcion: 'Construcción de interfaces web utilizando Angular.' },
    { id: 9, dia: 0, inicio: 15, fin: 16, sala: 'Sala C', titulo: 'Panel: Mujeres en tecnología', tipo: 'Panel', expositor: 'Panel de invitadas', descripcion: 'Trayectorias y oportunidades en el sector tecnológico.' },
    { id: 10, dia: 0, inicio: 16, fin: 17, sala: 'Sala A', titulo: 'Cierre del día', tipo: 'Conferencia', expositor: 'Comité organizador', descripcion: 'Resumen de la jornada.' },
    { id: 11, dia: 1, inicio: 9, fin: 10, sala: 'Sala A', titulo: 'Transformación digital', tipo: 'Conferencia', expositor: 'María Duarte', descripcion: 'Estrategias para impulsar la transformación digital.' },
    { id: 12, dia: 1, inicio: 10, fin: 12, sala: 'Sala B', titulo: 'Taller de APIs', tipo: 'Taller', expositor: 'Equipo backend', descripcion: 'Diseño, documentación y consumo de APIs.' },
    { id: 13, dia: 1, inicio: 13, fin: 14, sala: 'Sala C', titulo: 'Panel de emprendimiento', tipo: 'Panel', expositor: 'Emprendedores invitados', descripcion: 'Experiencias de emprendimientos tecnológicos.' },
    { id: 14, dia: 2, inicio: 9, fin: 10, sala: 'Sala D', titulo: 'Networking y comunidad', tipo: 'Networking', expositor: 'Comunidad Eventia', descripcion: 'Encuentro abierto para los participantes.' },
    { id: 15, dia: 2, inicio: 10, fin: 12, sala: 'Sala A', titulo: 'Seguridad por diseño', tipo: 'Conferencia', expositor: 'Especialistas invitados', descripcion: 'Principios de seguridad desde el diseño de soluciones.' },
    { id: 16, dia: 2, inicio: 14, fin: 16, sala: 'Sala B', titulo: 'Laboratorio de datos', tipo: 'Taller', expositor: 'Equipo de datos', descripcion: 'Ejercicios prácticos de análisis de datos.' },
  ];

  readonly actividadesFiltradas = computed(() => {
    const q = this.busqueda().trim().toLocaleLowerCase();
    return this.actividades.filter(a =>
      a.dia === this.diaSeleccionado() &&
      (this.salaFiltro() === 'Todas' || a.sala === this.salaFiltro()) &&
      (this.tipoFiltro() === 'Todos' || a.tipo === this.tipoFiltro()) &&
      (!q || `${a.titulo} ${a.expositor}`.toLocaleLowerCase().includes(q))
    );
  });

  readonly seleccionada = computed(() =>
    this.actividades.find(a => a.id === this.actividadSeleccionada()) ?? null
  );

  constructor(route: ActivatedRoute) {
    const rol = route.snapshot.queryParamMap.get('rol');
    this.esOrganizador.set(rol === 'organizador' || rol === 'admin');
  }

  seleccionarDia(index: number): void {
    this.diaSeleccionado.set(index);
    const primera = this.actividades.find(a => a.dia === index);
    this.actividadSeleccionada.set(primera?.id ?? null);
  }

  seleccionarActividad(id: number): void {
    this.actividadSeleccionada.set(id);
  }

  tieneActividad(sala: string, hora: number): Actividad | undefined {
    return this.actividadesFiltradas().find(a => a.sala === sala && a.inicio === hora);
  }

  hora(valor: number): string {
    return `${String(valor).padStart(2, '0')}:00`;
  }

  alternarAgendaPersonal(id: number): void {
    this.agendaPersonal.update(ids => ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]);
  }

  estaEnAgenda(id: number): boolean {
    return this.agendaPersonal().includes(id);
  }

  imprimir(): void {
    window.print();
  }
}
