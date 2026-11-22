# Servicio de generación de la tarjeta de inscripción en PDF.
#
# Es la credencial que el participante imprime y lleva a las actividades
# del evento: muestra sus datos, el número de inscripción con un código de
# barras (Code 39) que el personal puede escanear en la pantalla de
# acreditación, y la agenda de actividades a las que puede asistir.

from dataclasses import dataclass, field
from datetime import date, time

from fpdf import FPDF

from app.services.certificado_pdf import _fecha, _rango_fechas, _texto


@dataclass(frozen=True)
class ActividadTarjeta:
    titulo: str
    fecha: date
    hora_inicio: time
    hora_fin: time
    lugar: str | None


@dataclass(frozen=True)
class DatosTarjeta:
    id_inscripcion: int
    participante: str
    documento: str | None
    institucion: str | None
    rol: str
    evento: str
    fecha_inicio_evento: date
    fecha_fin_evento: date
    lugar_evento: str | None
    actividades: list[ActividadTarjeta] = field(default_factory=list)


def codigo_inscripcion(id_inscripcion: int) -> str:
    # Mismo formato que acepta la búsqueda de la pantalla de acreditación.
    return f"INS-{id_inscripcion:06d}"


AZUL = (37, 99, 235)
TEXTO = (23, 32, 51)
SECUNDARIO = (102, 112, 133)


def _dato(pdf: FPDF, x: float, y: float, ancho: float, etiqueta: str, valor: str) -> None:
    pdf.set_xy(x, y)
    pdf.set_text_color(*SECUNDARIO)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(ancho, 4, _texto(etiqueta.upper()))
    pdf.set_xy(x, y + 4)
    pdf.set_text_color(*TEXTO)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(ancho, 5, _texto(valor))


def generar_tarjeta_inscripcion_pdf(datos: DatosTarjeta) -> bytes:
    pdf = FPDF(orientation="portrait", format="A4")
    pdf.set_title(_texto(f"Tarjeta de inscripción - {datos.participante}"))
    pdf.set_author("Eventia")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    codigo = codigo_inscripcion(datos.id_inscripcion)

    # --- Tarjeta recortable (parte superior de la hoja) ---
    x, y, ancho, alto = 25, 18, 160, 104
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.3)
    pdf.set_dash_pattern(dash=2, gap=1.5)
    pdf.rect(x - 4, y - 4, ancho + 8, alto + 8)
    pdf.set_dash_pattern()

    pdf.set_xy(x - 4, y - 9)
    pdf.set_text_color(*SECUNDARIO)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(ancho + 8, 4, _texto("Recortá por la línea punteada y llevá la tarjeta a todas las actividades."), align="C")

    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.6)
    pdf.rect(x, y, ancho, alto)

    # Banda superior.
    pdf.set_fill_color(*AZUL)
    pdf.rect(x, y, ancho, 16, style="F")
    pdf.set_xy(x + 6, y + 3)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(80, 5, "EVENTIA")
    pdf.set_xy(x + 6, y + 8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(100, 6, _texto("TARJETA DE INSCRIPCIÓN"))
    pdf.set_xy(x + ancho - 56, y + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(50, 4, _texto("N° de inscripción"), align="R")
    pdf.set_xy(x + ancho - 56, y + 8)
    pdf.set_font("Courier", "B", 13)
    pdf.cell(50, 6, codigo, align="R")

    # Participante.
    pdf.set_xy(x + 6, y + 22)
    pdf.set_text_color(*TEXTO)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(ancho - 12, 10, _texto(datos.participante))

    pdf.set_xy(x + 6, y + 32)
    pdf.set_text_color(*AZUL)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(ancho - 12, 6, _texto(datos.rol.upper()))

    columna = (ancho - 12) / 2
    _dato(pdf, x + 6, y + 42, columna, "Documento", datos.documento or "-")
    _dato(pdf, x + 6 + columna, y + 42, columna, "Institución", datos.institucion or "-")

    # Evento.
    pdf.set_draw_color(229, 231, 235)
    pdf.set_line_width(0.3)
    pdf.line(x + 6, y + 55, x + ancho - 6, y + 55)
    _dato(pdf, x + 6, y + 58, ancho - 12, "Evento", datos.evento)
    _dato(
        pdf,
        x + 6,
        y + 68,
        columna,
        "Fechas",
        _rango_fechas(datos.fecha_inicio_evento, datos.fecha_fin_evento).capitalize(),
    )
    _dato(pdf, x + 6 + columna, y + 68, columna, "Lugar", datos.lugar_evento or "-")

    # Código de barras para escanear en la acreditación.
    # Code 39 en fpdf2: barra ancha = w, angosta = w/3; cada carácter ocupa
    # 6 angostas + 3 anchas + 1 separador angosto = 16/3 * w.
    barras = f"*{codigo}*"
    modulo = 0.9
    barras_ancho = len(barras) * 16 / 3 * modulo
    pdf.set_fill_color(0, 0, 0)
    pdf.code39(barras, x + (ancho - barras_ancho) / 2, y + 81, w=modulo, h=13)
    pdf.set_xy(x, y + 96)
    pdf.set_text_color(*SECUNDARIO)
    pdf.set_font("Courier", "", 8)
    pdf.cell(ancho, 4, codigo, align="C")

    # --- Agenda de actividades (parte inferior, no se recorta) ---
    pdf.set_xy(20, y + alto + 14)
    pdf.set_text_color(*TEXTO)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(170, 7, _texto("Actividades del evento"))
    pdf.ln(8)
    pdf.set_x(20)
    pdf.set_text_color(*SECUNDARIO)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        170,
        5,
        _texto(
            "Tu inscripción te habilita a todas las actividades del evento. "
            "Presentá la tarjeta al ingresar a cada una para registrar tu asistencia."
        ),
    )
    pdf.ln(3)

    if not datos.actividades:
        pdf.set_x(20)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(170, 6, _texto("La agenda de actividades todavía no fue publicada."))
        return bytes(pdf.output())

    columnas = (("Fecha", 24), ("Horario", 26), ("Actividad", 80), ("Lugar", 40))
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(229, 231, 235)
    pdf.set_text_color(*SECUNDARIO)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(20)
    for titulo, ancho_col in columnas:
        pdf.cell(ancho_col, 7, titulo.upper(), border="B", fill=True)
    pdf.ln()

    pdf.set_text_color(*TEXTO)
    pdf.set_font("Helvetica", "", 9)
    for actividad in datos.actividades:
        pdf.set_x(20)
        valores = (
            _fecha(actividad.fecha),
            f"{actividad.hora_inicio:%H:%M} - {actividad.hora_fin:%H:%M}",
            actividad.titulo,
            actividad.lugar or "-",
        )
        for valor, (_, ancho_col) in zip(valores, columnas):
            texto = _texto(valor)
            # Recorta textos largos para mantener una fila por actividad.
            while pdf.get_string_width(texto) > ancho_col - 2 and len(texto) > 3:
                texto = texto[:-4] + "..."
            pdf.cell(ancho_col, 7, texto, border="B")
        pdf.ln()

    return bytes(pdf.output())
