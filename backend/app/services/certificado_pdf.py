# Servicio de generación del documento PDF de un certificado.
#
# Arma un certificado A4 apaisado con los datos del participante y del
# evento, el porcentaje de asistencia y el código de validación con la URL
# pública donde cualquiera puede verificarlo.

from dataclasses import dataclass
from datetime import date, datetime

from fpdf import FPDF

from app.core.config import settings


TITULOS_POR_TIPO = {
    "participacion": "CERTIFICADO DE PARTICIPACIÓN",
}


@dataclass(frozen=True)
class DatosCertificado:
    codigo_validacion: str
    tipo: str
    fecha_emision: datetime
    participante: str
    evento: str
    fecha_inicio_evento: date
    fecha_fin_evento: date
    porcentaje_asistencia: float


def url_verificacion(codigo: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/certificados/verificar/{codigo}"


def _texto(valor: str) -> str:
    # Las fuentes estándar del PDF solo cubren latin-1 (incluye tildes y ñ);
    # cualquier otro carácter se reemplaza en lugar de fallar.
    return valor.encode("latin-1", "replace").decode("latin-1")


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def _rango_fechas(inicio: date, fin: date) -> str:
    if inicio == fin:
        return f"el {_fecha(inicio)}"
    return f"del {_fecha(inicio)} al {_fecha(fin)}"


def generar_certificado_pdf(datos: DatosCertificado) -> bytes:
    pdf = FPDF(orientation="landscape", format="A4")
    pdf.set_title(_texto(f"Certificado - {datos.participante}"))
    pdf.set_author("Eventia")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    ancho = pdf.w - 40

    # Marco decorativo.
    pdf.set_draw_color(31, 78, 121)
    pdf.set_line_width(1.5)
    pdf.rect(10, 10, pdf.w - 20, pdf.h - 20)
    pdf.set_line_width(0.4)
    pdf.rect(14, 14, pdf.w - 28, pdf.h - 28)

    pdf.set_xy(20, 30)
    pdf.set_text_color(31, 78, 121)
    pdf.set_font("Helvetica", "B", 30)
    titulo = TITULOS_POR_TIPO.get(datos.tipo, "CERTIFICADO")
    pdf.cell(ancho, 14, _texto(titulo), align="C")

    pdf.set_xy(20, 58)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 15)
    pdf.cell(ancho, 10, "Se certifica que", align="C")

    pdf.set_xy(20, 72)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(ancho, 14, _texto(datos.participante), align="C")

    pdf.set_xy(30, 94)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 15)
    pdf.multi_cell(
        ancho - 20,
        9,
        _texto(
            f'participó del evento "{datos.evento}", realizado '
            f"{_rango_fechas(datos.fecha_inicio_evento, datos.fecha_fin_evento)}, "
            f"con una asistencia del {datos.porcentaje_asistencia:g}% "
            "de las actividades."
        ),
        align="C",
    )

    pdf.set_xy(20, 135)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(
        ancho,
        8,
        _texto(f"Fecha de emisión: {_fecha(datos.fecha_emision)}"),
        align="C",
    )

    # Datos de validación al pie.
    pdf.set_xy(20, pdf.h - 42)
    pdf.set_text_color(31, 78, 121)
    pdf.set_font("Courier", "B", 12)
    pdf.cell(
        ancho,
        7,
        _texto(f"Código de validación: {datos.codigo_validacion}"),
        align="C",
    )
    pdf.set_xy(20, pdf.h - 34)
    pdf.set_text_color(90, 90, 90)
    pdf.set_font("Helvetica", "", 10)
    url = url_verificacion(datos.codigo_validacion)
    pdf.cell(
        ancho,
        6,
        _texto(f"Verificá la autenticidad de este certificado en {url}"),
        align="C",
        link=url,
    )

    return bytes(pdf.output())
