# Exporta el esquema OpenAPI de la app FastAPI a docs/openapi.json, que es
# el archivo que carga la documentación interactiva (docs/index.html).
# Ejecutar desde la carpeta backend cada vez que se agregue o cambie un
# endpoint:
#
#     python docs/generate_openapi.py
#
# No necesita la base de datos levantada: solo importa la app.
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

# Servidor por defecto contra el que Swagger ejecuta las peticiones
# ("Try it out") cuando el archivo se abre fuera del backend.
DEFAULT_SERVER = {"url": "http://localhost:8000", "description": "Backend local (uvicorn)"}


def main() -> None:
    schema = app.openapi()
    schema["servers"] = [{"url": "/", "description": "Mismo servidor que sirve la documentación"}, DEFAULT_SERVER]
    output = Path(__file__).resolve().parent / "openapi.json"
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(ops) for ops in schema["paths"].values())
    print(f"{output} generado ({total} endpoints)")


if __name__ == "__main__":
    main()
