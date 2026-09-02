# BaseSettings: clase base de pydantic-settings que permite definir la
# configuración de la app como atributos tipados, leyendo sus valores desde
# variables de entorno (o un archivo .env) en vez de tenerlos hardcodeados.
# SettingsConfigDict: permite configurar de dónde y cómo se leen esos valores.
from pydantic_settings import BaseSettings, SettingsConfigDict


# Configuración global de la aplicación: credenciales de conexión a la base
# de datos y parámetros para generar/validar los tokens JWT de autenticación.
# Cada atributo puede sobreescribirse mediante una variable de entorno con
# el mismo nombre (en mayúsculas) o desde el archivo .env.
class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://eventia:eventia@localhost:5432/eventia"
    jwt_secret_key: str = "change-this-development-secret-key-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Indica que los valores se pueden leer desde un archivo ".env" y que
    # las variables de entorno adicionales no declaradas aquí se ignoran.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Instancia única de la configuración, importada por el resto de la app
# para acceder a estos valores (ej: settings.jwt_secret_key).
settings = Settings()
