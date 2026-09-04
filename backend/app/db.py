# Generator: tipo estándar de Python usado para anotar funciones que
# producen valores con "yield" (como get_db, que entrega una sesión de BD).
from collections.abc import Generator

# create_engine: crea el motor de conexión de SQLAlchemy hacia la base de
# datos, a partir de la URL de conexión.
from sqlalchemy import create_engine
# DeclarativeBase: clase base para definir modelos ORM (tablas como clases
# de Python). Session: representa una sesión/transacción de trabajo con la
# base de datos. sessionmaker: fábrica que crea instancias de Session
# configuradas de una manera particular.
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Configuración de la app, de donde se obtiene la URL de conexión a la BD.
from app.core.config import settings


# Motor de conexión a la base de datos. pool_pre_ping=True hace que, antes
# de reutilizar una conexión del pool, se verifique que siga viva (evita
# errores por conexiones cortadas por inactividad).
engine = create_engine(settings.database_url, pool_pre_ping=True)
# Fábrica de sesiones de base de datos ligadas al engine. autoflush=False y
# autocommit=False dan control manual sobre cuándo se envían/confirman los
# cambios (se hace explícitamente con db.commit()).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Clase base de la que heredan todos los modelos ORM (ver app/models.py).
# SQLAlchemy usa esta base para saber qué clases representan tablas.
class Base(DeclarativeBase):
    pass


# Dependencia de FastAPI que entrega una sesión de base de datos por
# petición y garantiza que se cierre al finalizar (incluso si ocurre un
# error), evitando dejar conexiones abiertas.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
