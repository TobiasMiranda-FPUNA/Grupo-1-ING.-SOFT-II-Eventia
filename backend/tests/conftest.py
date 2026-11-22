import pytest

from app.core.config import settings


# Los tests nunca usan un servidor SMTP real, aunque el .env local tenga
# uno configurado; los que prueban el envío lo simulan explícitamente.
@pytest.fixture(autouse=True)
def sin_smtp(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
