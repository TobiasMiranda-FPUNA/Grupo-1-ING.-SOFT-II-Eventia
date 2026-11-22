from datetime import date, datetime

from app.services.certificado_pdf import DatosCertificado
from app.services.correo import _armar_mensaje_certificado, correo_configurado


def _datos():
    return DatosCertificado(
        codigo_validacion="ABC123",
        tipo="participacion",
        fecha_emision=datetime(2026, 11, 13),
        participante="Hugo Villagra",
        evento="Congreso <Nacional>",
        fecha_inicio_evento=date(2026, 11, 10),
        fecha_fin_evento=date(2026, 11, 12),
        porcentaje_asistencia=100,
    )


def test_sin_host_el_correo_no_esta_configurado():
    assert correo_configurado() is False


def test_mensaje_incluye_texto_html_y_pdf_adjunto():
    mensaje = _armar_mensaje_certificado("hugo@example.com", _datos(), b"%PDF-1.4 demo")

    assert mensaje["To"] == "hugo@example.com"
    assert "Congreso <Nacional>" in mensaje["Subject"]

    texto = mensaje.get_body(preferencelist=("plain",)).get_content()
    html = mensaje.get_body(preferencelist=("html",)).get_content()
    assert "ABC123" in texto and "/certificados/verificar/ABC123" in texto
    assert "Congreso &lt;Nacional&gt;" in html

    adjuntos = list(mensaje.iter_attachments())
    assert len(adjuntos) == 1
    assert adjuntos[0].get_filename() == "certificado-ABC123.pdf"
    assert adjuntos[0].get_content() == b"%PDF-1.4 demo"
