import pytest
import os
import sys

# 1. AGREGAR RUTAS AL PYTHONPATH

# Ruta a la carpeta "Proyecto"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Ruta a la carpeta "v2" (donde están app.py, model.py, config.py, etc.)
V2_ROOT = os.path.join(PROJECT_ROOT, "v2")
sys.path.insert(0, V2_ROOT)

# Importar la app y db desde v2
from v2.app import app, db


# 2. FIXTURE PARA CLIENTE DE PRUEBA

@pytest.fixture
def client():
    """Configura la app para pruebas y devuelve un cliente de prueba."""

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"

    # No usamos db.create_all porque app.py tiene Postgres
    # y para /register NO se usa la BD.

    with app.test_client() as testing_client:
        yield testing_client


# 3. TESTS

# Registro exitoso
def test_register_success_message(client):
    """Test: Registro exitoso."""

    response = client.post(
        "/register",
        data={
            "name": "Nicole",
            "email": "nicole@test.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "terms": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    html = response.data.decode("utf-8")
    assert "¡Cuenta creada exitosamente para nicole@test.com!" in html

# Registro con contraseñas que no coinciden
def test_register_password_mismatch(client):
    """Test: Cuando las contraseñas NO coinciden."""

    response = client.post(
        "/register",
        data={
            "name": "Nicole",
            "email": "nicole@test.com",
            "password": "abc123",
            "confirm_password": "def456",
            "terms": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    html = response.data.decode("utf-8")
    assert "Las contraseñas no coinciden" in html

# Registro sin aceptar términos
def test_register_without_terms(client):
    """Test: Usuario NO acepta los términos."""

    response = client.post(
        "/register",
        data={
            "name": "Nicole",
            "email": "nicole@test.com",
            "password": "abc123",
            "confirm_password": "abc123",
            # NO enviamos "terms"
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    html = response.data.decode("utf-8")
    assert "Debes aceptar los términos y condiciones" in html
