from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.users import require_any_system_role
from app.db import get_db
from app.models import Usuario
from app.schemas import MetricasEventoResumen
from app.services.metricas import resumen_eventos


router = APIRouter(
    prefix="/api/v1/metricas",
    tags=["Métricas"],
)

metrics_viewer_required = Depends(
    require_any_system_role("organizador", "administrador")
)


# Resumen de inscriptos, ocupación y asistencia de todos los eventos.
# El detalle de un evento está en GET /api/v1/eventos/{id}/dashboard.
@router.get(
    "/eventos",
    response_model=list[MetricasEventoResumen],
)
def listar_metricas_eventos(
    db: Session = Depends(get_db),
    _: Usuario = metrics_viewer_required,
) -> list[MetricasEventoResumen]:
    return resumen_eventos(db)

