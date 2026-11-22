# Servicio de envío de correos (certificados y tarjetas de inscripción).
#
# Usa SMTP con la configuración de app/core/config.py. Si no hay servidor
# configurado, correo_configurado() devuelve False y quien llama decide qué
# hacer (los certificados se emiten igual, solo no se envían).

import smtplib
import ssl
from email.message import EmailMessage
from html import escape

from app.core.config import settings
from app.services.certificado_pdf import DatosCertificado, _rango_fechas, url_verificacion
from app.services.tarjeta_inscripcion_pdf import DatosTarjeta, codigo_inscripcion


class CorreoError(Exception):
    """El servidor SMTP rechazó o no pudo entregar el mensaje."""


def correo_configurado() -> bool:
    return bool(settings.smtp_host and (settings.smtp_from or settings.smtp_user))


def _remitente() -> str:
    return settings.smtp_from or settings.smtp_user or ""


def _armar_mensaje_certificado(
    destinatario: str,
    datos: DatosCertificado,
    pdf: bytes,
) -> EmailMessage:
    url = url_verificacion(datos.codigo_validacion)

    mensaje = EmailMessage()
    mensaje["Subject"] = f"Tu certificado de {datos.evento}"
    mensaje["From"] = _remitente()
    mensaje["To"] = destinatario

    mensaje.set_content(
        f"Hola {datos.participante}:\n\n"
        f"¡Felicitaciones por culminar el evento \"{datos.evento}\"!\n"
        "Adjuntamos tu certificado de participación en PDF.\n\n"
        f"Código de validación: {datos.codigo_validacion}\n"
        f"Podés verificar su autenticidad en: {url}\n\n"
        "Equipo Eventia"
    )
    mensaje.add_alternative(
        f"""\
<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f5f7fb;font-family:Arial,sans-serif;color:#172033">
    <div style="max-width:560px;margin:24px auto;background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:28px">
      <p style="margin:0 0 6px;color:#2563eb;font-size:12px;font-weight:800;letter-spacing:.11em">EVENTIA · CERTIFICADOS</p>
      <h1 style="margin:0 0 16px;font-size:22px">¡Felicitaciones, {escape(datos.participante)}!</h1>
      <p>Culminaste el evento <strong>{escape(datos.evento)}</strong>. Adjuntamos tu certificado de participación en PDF.</p>
      <p style="margin:20px 0 6px;color:#667085;font-size:13px">Código de validación</p>
      <p style="margin:0 0 20px;font-family:monospace;font-size:16px;font-weight:700">{escape(datos.codigo_validacion)}</p>
      <a href="{escape(url)}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;font-weight:700;padding:11px 18px;border-radius:9px">Verificar certificado</a>
      <p style="margin:24px 0 0;color:#98a2b3;font-size:12px">Este correo fue enviado automáticamente por Eventia.</p>
    </div>
  </body>
</html>
""",
        subtype="html",
    )
    mensaje.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=f"certificado-{datos.codigo_validacion}.pdf",
    )
    return mensaje


def _enviar(mensaje: EmailMessage) -> None:
    timeout = settings.smtp_timeout_seconds
    try:
        if settings.smtp_use_ssl:
            servidor = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=timeout,
                context=ssl.create_default_context(),
            )
        else:
            servidor = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)

        with servidor:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                servidor.starttls(context=ssl.create_default_context())
            if settings.smtp_user and settings.smtp_password:
                servidor.login(settings.smtp_user, settings.smtp_password)
            servidor.send_message(mensaje)
    except (smtplib.SMTPException, OSError) as exc:
        raise CorreoError(str(exc)) from exc


def enviar_certificado(destinatario: str, datos: DatosCertificado, pdf: bytes) -> None:
    _enviar(_armar_mensaje_certificado(destinatario, datos, pdf))


def _armar_mensaje_tarjeta(
    destinatario: str,
    datos: DatosTarjeta,
    pdf: bytes,
) -> EmailMessage:
    codigo = codigo_inscripcion(datos.id_inscripcion)
    fechas = _rango_fechas(datos.fecha_inicio_evento, datos.fecha_fin_evento)

    mensaje = EmailMessage()
    mensaje["Subject"] = f"Tu tarjeta de inscripción - {datos.evento}"
    mensaje["From"] = _remitente()
    mensaje["To"] = destinatario

    mensaje.set_content(
        f"Hola {datos.participante}:\n\n"
        f"Tu inscripción al evento \"{datos.evento}\" ({fechas}) está confirmada.\n"
        "Adjuntamos tu tarjeta de inscripción en PDF: imprimila y llevala a "
        "todas las actividades para que el personal te identifique.\n\n"
        f"N° de inscripción: {codigo}\n\n"
        "Equipo Eventia"
    )
    mensaje.add_alternative(
        f"""\
<!doctype html>
<html lang="es">
  <body style="margin:0;background:#f5f7fb;font-family:Arial,sans-serif;color:#172033">
    <div style="max-width:560px;margin:24px auto;background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:28px">
      <p style="margin:0 0 6px;color:#2563eb;font-size:12px;font-weight:800;letter-spacing:.11em">EVENTIA · INSCRIPCIÓN</p>
      <h1 style="margin:0 0 16px;font-size:22px">¡Tu inscripción está confirmada, {escape(datos.participante)}!</h1>
      <p>Te esperamos en <strong>{escape(datos.evento)}</strong>, {escape(fechas)}.</p>
      <p>Adjuntamos tu <strong>tarjeta de inscripción</strong> en PDF. Imprimila y llevala a todas las actividades: el personal la usa para identificarte y registrar tu asistencia.</p>
      <p style="margin:20px 0 6px;color:#667085;font-size:13px">N° de inscripción</p>
      <p style="margin:0;font-family:monospace;font-size:18px;font-weight:700">{escape(codigo)}</p>
      <p style="margin:24px 0 0;color:#98a2b3;font-size:12px">Este correo fue enviado automáticamente por Eventia.</p>
    </div>
  </body>
</html>
""",
        subtype="html",
    )
    mensaje.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=f"tarjeta-{codigo}.pdf",
    )
    return mensaje


def enviar_tarjeta_inscripcion(destinatario: str, datos: DatosTarjeta, pdf: bytes) -> None:
    _enviar(_armar_mensaje_tarjeta(destinatario, datos, pdf))
