import pytest
import os
import sys

# 1. AGREGAR RUTAS AL PYTHONPATH
# (POR QUÉ ESTO ES IMPORTANTE): Esta sección asegura que, sin importar desde
# dónde se ejecute el comando 'pytest', Python siempre sabrá cómo encontrar
# los archivos de tu aplicación en la carpeta 'v2'.
# Es clave para que el entorno sea robusto.

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
    """
    Crea y configura una instancia de la aplicación para cada prueba.
    
    Esta 'fixture' es el corazón del entorno de pruebas. Proporciona
    un 'cliente' que simula ser un navegador web, permitiéndonos
    enviar peticiones (POST, GET) a nuestras rutas y verificar
    sus respuestas de forma aislada y segura.
    """
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    
    # Se usa una base de datos temporal 'en memoria'.
    # Aunque estas pruebas no la usan, es una buena práctica configurarla
    # para evitar cualquier intento de conexión a la base de datos real.
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.test_client() as testing_client:
        yield testing_client


# 3. TESTS

# Registro exitoso
def test_register_success_message(client):
    """
    Prueba el 'caso exitoso' (happy path) del registro.
    
    - VALIDA: Que un usuario que llena todos los campos correctamente
      y acepta los términos puede registrarse.
    - ESPERA: Una respuesta exitosa (código 200) y que la página
      muestre el mensaje de bienvenida confirmando la creación de la cuenta.
    """
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
    """
    Prueba el 'caso límite' donde las contraseñas no coinciden.
    
    - VALIDA: Que el sistema previene el registro si los campos de
      contraseña y confirmación son diferentes.
    - ESPERA: Que la página recargue y muestre un mensaje de error
      específico sobre la no coincidencia de las contraseñas.
    """
    response = client.post(
        "/register",
        data={
            "name": "Nicole",
            "email": "nicole@test.com",
            "password": "abc123",
            "confirm_password": "def456", # Contraseñas diferentes
            "terms": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Las contraseñas no coinciden" in html

# Registro sin aceptar términos
def test_register_without_terms(client):
    """
    Prueba el 'caso límite' donde el usuario no acepta los términos.
    
    - VALIDA: Que el sistema no permite el registro si el checkbox de
      'términos y condiciones' no está marcado.
    - ESPERA: Que la página recargue y muestre un mensaje de error
      indicando que los términos deben ser aceptados.
    """
    response = client.post(
        "/register",
        data={
            "name": "Nicole",
            "email": "nicole@test.com",
            "password": "abc123",
            "confirm_password": "abc123",
            # El campo "terms" se omite intencionalmente
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Debes aceptar los términos y condiciones" in html