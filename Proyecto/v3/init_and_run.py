#!/usr/bin/env python3
"""
Script de inicializacion de SmartBite
Espera a PostgreSQL y carga los datos a la base de datos si es necesario
"""
import sys
import time
import subprocess
import psycopg2


def wait_for_postgres(max_attempts=30):
    """
    Espera a que PostgreSQL esté listo
    """

    print("Esperando a que PostgreSQL esté listo...")
    for attempt in range(max_attempts):
        try:
            conn = psycopg2.connect(
                host="db",
                port=5432,
                user="postgres",
                password="password",
                database="postgres",
                connect_timeout=3,
            )
            conn.close()
            print("PostgreSQL está listo")
            return True
        except psycopg2.OperationalError:
            print(f"  Intento {attempt + 1}/{max_attempts}...")
            time.sleep(2)

    # Si llega aqui, significa que no se pudo conectar en los intentos que se le dieron
    print("ERROR: PostgreSQL no respondió a tiempo")
    return False


# Por ahora solo está para la base de datos del modelo
# En el futuro se pondrá la base de datos del usuario xd
def create_databases():
    """
    Crea las bases de datos necesarias
    """

    print("Verificando bases de datos...")
    try:
        conn = psycopg2.connect(
            host="db",
            port=5432,
            user="postgres",
            password="password",
            database="postgres",
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Crear DB de recetas
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='v2'")
        if not cursor.fetchone():
            cursor.execute("CREATE DATABASE v2")
            print("Base de datos 'v2' creada")
        else:
            print("Base de datos 'v2' ya existe")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"ERROR al crear bases de datos: {e}")
        return False


def check_recipes_loaded():
    """
    Verifica si ya hay recetas cargadas en la base de datos.
    Si no hay recetas, se inicializan.
    """

    try:
        conn = psycopg2.connect(
            host="db",
            port=5432,
            user="postgres",
            password="password",
            database="v2",
            connect_timeout=5,
        )
        cursor = conn.cursor()

        # Primero hay que verificar si la tabla existe
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'recipes'
            )
        """
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            cursor.close()
            conn.close()
            return 0

        # Si existe, contar las recetas
        cursor.execute("SELECT COUNT(*) FROM recipes")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count

    # Si hay error, probablemente es porque la base de datos es nueva
    except Exception as e:
        print(f"No se pudo verificar recetas (probablemente DB nueva): {e}")
        return 0


def initialize_recipe_database():
    """
    Inicializa la base de datos de recetas solo si está vacía
    """

    # Primero se verifica si la base de datos ya tiene recetas
    recipe_count = check_recipes_loaded()

    if recipe_count > 0:
        print(
            f"Base de datos ya tiene {recipe_count} recetas. Saltando inicializacion..."
        )
        return True

    print("Inicializando base de datos de recetas...")
    print(
        "NOTA: Esto puede tardar 35-45 minutos debido añ tamaño del dataset de recetas"
    )

    try:
        import database_builder

        database_builder.main()
        print("\n")
        print("Base de datos inicializada correctamente")
        return True
    except Exception as e:
        print(f"ERROR al inicializar la base de datos: {e}")
        import traceback

        traceback.print_exc()
        return False


def start_application():
    """
    Inicia la aplicación
    """
    print("Iniciando aplicación Flask...")

    # Ejecuta el comando que se pasó como argumentos
    cmd = (
        sys.argv[1:]
        if len(sys.argv) > 1
        else [
            "gunicorn",
            "--bind",
            "0.0.0.0:5000",
            "app:app",
            "--workers",
            "2",
            "--threads",
            "4",
        ]
    )
    subprocess.run(cmd)


if __name__ == "__main__":
    if not wait_for_postgres():
        sys.exit(1)

    if not create_databases():
        sys.exit(1)

    if not initialize_recipe_database():
        sys.exit(1)

    start_application()
