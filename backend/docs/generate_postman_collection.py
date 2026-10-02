# Genera docs/eventia.postman_collection.json a partir del esquema OpenAPI
# de la app FastAPI, para probar todos los endpoints desde clientes de API
# (Postman, Insomnia, Bruno, Thunder Client, etc.).
#
#     python docs/generate_postman_collection.py
#
# La colección incluye:
#   - Una carpeta por grupo (tag) de endpoints, igual que en Swagger.
#   - Variables {{baseUrl}} y {{token}}.
#   - Requests de login (administrador y organizador) que guardan el token
#     en {{token}} automáticamente; el resto de los endpoints protegidos lo
#     envían como "Authorization: Bearer {{token}}".
#   - Bodies JSON de ejemplo armados a partir de los esquemas.
#
# No necesita la base de datos levantada: solo importa la app.
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

BASE_URL = f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}"
OUTPUT = Path(__file__).resolve().parent / "eventia.postman_collection.json"

# Usuarios de ejemplo cargados por sql/cargar_datos_ejemplo.sql (solo desarrollo).
SAMPLE_USERS = {
    "administrador": ("admin@eventia.test", "Admin123!"),
    "organizador": ("organizador@eventia.test", "Organizador123!"),
}

# Script que se ejecuta después del login y guarda el token en {{token}}.
SAVE_TOKEN_SCRIPT = [
    "if (pm.response.code === 200) {",
    "    const token = pm.response.json().access_token;",
    "    pm.collectionVariables.set('token', token);",
    "    console.log('Token guardado en {{token}}');",
    "}",
]


def resolve(schema: dict, components: dict) -> dict:
    """Sigue las referencias $ref hasta el esquema real."""
    while "$ref" in schema:
        schema = components[schema["$ref"].split("/")[-1]]
    return schema


def sample_value(schema: dict, components: dict, name: str = "", depth: int = 0):
    """Arma un valor de ejemplo a partir de un esquema JSON."""
    schema = resolve(schema, components)
    if depth > 5:
        return None
    if "example" in schema:
        return schema["example"]
    if schema.get("examples"):
        return schema["examples"][0]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            options = [s for s in schema[key] if resolve(s, components).get("type") != "null"]
            if options:
                return sample_value(options[0], components, name, depth + 1)
            return None

    kind = schema.get("type")
    fmt = schema.get("format", "")
    if kind == "object" or "properties" in schema:
        return {
            prop: sample_value(sub, components, prop, depth + 1)
            for prop, sub in schema.get("properties", {}).items()
        }
    if kind == "array":
        return [sample_value(schema.get("items", {}), components, name, depth + 1)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    if kind == "string":
        if fmt == "email" or "email" in name:
            return "usuario@eventia.test"
        if fmt == "date":
            return "2026-11-15"
        if fmt == "date-time":
            return "2026-11-15T09:00:00"
        if fmt == "time":
            return "09:00:00"
        if fmt == "password" or "password" in name:
            return "Secreto123!"
        return f"texto de ejemplo ({name})" if name else "texto"
    return None


def build_request(path: str, method: str, operation: dict, components: dict) -> dict:
    # Postman usa ":param" para las variables de ruta en lugar de "{param}".
    segments = [s for s in path.strip("/").split("/") if s]
    postman_segments = [f":{s[1:-1]}" if s.startswith("{") else s for s in segments]

    path_vars, query = [], []
    for param in operation.get("parameters", []):
        value = sample_value(param.get("schema", {}), components, param["name"])
        entry = {
            "key": param["name"],
            "value": "" if value is None else str(value).lower() if isinstance(value, bool) else str(value),
            "description": param.get("description", ""),
        }
        if param["in"] == "path":
            path_vars.append(entry)
        elif param["in"] == "query":
            entry["disabled"] = not param.get("required", False)
            query.append(entry)

    url = {
        "raw": "{{baseUrl}}/" + "/".join(postman_segments),
        "host": ["{{baseUrl}}"],
        "path": postman_segments,
    }
    if path_vars:
        url["variable"] = path_vars
    if query:
        url["query"] = query
        enabled = [f"{q['key']}={q['value']}" for q in query if not q["disabled"]]
        if enabled:
            url["raw"] += "?" + "&".join(enabled)

    request = {
        "method": method.upper(),
        "header": [],
        "url": url,
        "description": operation.get("description", ""),
    }
    # Los endpoints públicos no envían token; los protegidos heredan el
    # Bearer {{token}} configurado a nivel de colección.
    if not operation.get("security"):
        request["auth"] = {"type": "noauth"}

    content = operation.get("requestBody", {}).get("content", {})
    if "application/json" in content:
        body = sample_value(content["application/json"].get("schema", {}), components)
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, ensure_ascii=False, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    return request


def login_item(role: str, email: str, password: str) -> dict:
    return {
        "name": f"Login como {role} (guarda {{{{token}}}})",
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": SAVE_TOKEN_SCRIPT}}],
        "request": {
            "method": "POST",
            "auth": {"type": "noauth"},
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "url": {
                "raw": "{{baseUrl}}/api/v1/auth/login",
                "host": ["{{baseUrl}}"],
                "path": ["api", "v1", "auth", "login"],
            },
            "body": {
                "mode": "raw",
                "raw": json.dumps({"email": email, "password": password}, indent=2),
                "options": {"raw": {"language": "json"}},
            },
            "description": f"Usuario de ejemplo de sql/cargar_datos_ejemplo.sql con rol {role}.",
        },
    }


def main() -> None:
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})

    # Carpetas en el mismo orden que los tags declarados en app/main.py.
    folders: dict[str, list] = {tag["name"]: [] for tag in schema.get("tags", [])}
    total = 0
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            tag = (operation.get("tags") or ["Otros"])[0]
            item = {
                "name": f"{method.upper()} {path} — {operation.get('summary', '')}".rstrip(" —"),
                "request": build_request(path, method, operation, components),
            }
            # El login genérico también guarda el token.
            if path.endswith("/auth/login"):
                item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": SAVE_TOKEN_SCRIPT}}]
            folders.setdefault(tag, []).append(item)
            total += 1

    auth_folder = "Autenticación"
    folders.setdefault(auth_folder, [])
    folders[auth_folder] = [login_item(r, e, p) for r, (e, p) in SAMPLE_USERS.items()] + folders[auth_folder]

    collection = {
        "info": {
            "name": schema["info"]["title"],
            "description": (
                "Colección generada desde el OpenAPI de Eventia "
                "(backend/docs/generate_postman_collection.py).\n\n"
                "1. Ejecutar un request de la carpeta **Autenticación** (login).\n"
                "2. El token queda guardado en `{{token}}` y se usa en los endpoints protegidos.\n"
                "   - Rol **administrador**: Parametrización (roles).\n"
                "   - Rol **organizador**: eventos, actividades y conferencistas."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
        "variable": [
            {"key": "baseUrl", "value": BASE_URL},
            {"key": "token", "value": ""},
        ],
        "item": [{"name": name, "item": items} for name, items in folders.items() if items],
    }

    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUTPUT} generado ({total} endpoints)")


if __name__ == "__main__":
    main()
