import os
from dataclasses import dataclass
from typing import ClassVar, Iterable

import psycopg2
from psycopg2.extensions import connection as PGConnection
from urllib.parse import urlparse



POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/TUTORIAL")

EXPECTED_COLUMNS = [
    "recipe_id",
    "name",
    "calories",
    "fat",
    "saturated_fat",
    "cholesterol",
    "sodium",
    "carbohydrates",
    "fiber",
    "sugar",
    "protein",
]

FEATURE_COLUMNS = EXPECTED_COLUMNS[2:]


@dataclass
class Recipe:
    recipe_id: int
    name: str
    calories: float
    fat: float
    saturated_fat: float
    cholesterol: float
    sodium: float
    carbohydrates: float
    fiber: float
    sugar: float
    protein: float


CREATE_TABLE_SQL = """
CREATE TABLE tutorial_recipes (
    recipe_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    calories DOUBLE PRECISION NOT NULL,
    fat DOUBLE PRECISION NOT NULL,
    saturated_fat DOUBLE PRECISION NOT NULL,
    cholesterol DOUBLE PRECISION NOT NULL,
    sodium DOUBLE PRECISION NOT NULL,
    carbohydrates DOUBLE PRECISION NOT NULL,
    fiber DOUBLE PRECISION NOT NULL,
    sugar DOUBLE PRECISION NOT NULL,
    protein DOUBLE PRECISION NOT NULL
);
"""

INSERT_SQL = """
INSERT INTO tutorial_recipes (
    name,
    calories,
    fat,
    saturated_fat,
    cholesterol,
    sodium,
    carbohydrates,
    fiber,
    sugar,
    protein
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING recipe_id;
"""

SELECT_ALL_SQL = """
SELECT
    recipe_id,
    name,
    calories,
    fat,
    saturated_fat,
    cholesterol,
    sodium,
    carbohydrates,
    fiber,
    sugar,
    protein
FROM tutorial_recipes
ORDER BY recipe_id;
"""

SEED_RECIPES: tuple[tuple[str, float, float, float, float, float, float, float, float, float], ...] = (
    (
        "Hello Smoothie",
        350.0,
        12.0,
        4.0,
        70.0,
        400.0,
        45.0,
        7.0,
        12.0,
        18.0,
    ),
    (
        "Quick Avocado Toast",
        550.0,
        18.0,
        6.0,
        80.0,
        650.0,
        65.0,
        10.0,
        20.0,
        28.0,
    ),
    (
        "Protein Bowl",
        450.0,
        15.0,
        5.0,
        75.0,
        550.0,
        50.0,
        9.0,
        16.0,
        24.0,
    ),
)


def ensure_database_exists() -> None:
    #Create the database named in POSTGRES_DSN if it doesn't exist
    try:
        parsed = urlparse(POSTGRES_DSN)
        dbname = parsed.path[1:] if parsed.path and parsed.path.startswith("/") else parsed.path
        if not dbname:
            return

        user = parsed.username or ''
        password = parsed.password or ''
        host = parsed.hostname or 'localhost'
        port = parsed.port or 5432

        admin_dsn = f"postgresql://{user}:{password}@{host}:{port}/postgres"

        with psycopg2.connect(admin_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(f'CREATE DATABASE "{dbname}";')
                    conn.commit()
    except Exception:
        try:
            import traceback

            traceback.print_exc()
        except Exception:
            pass


class PostgresConnectionSingleton:
    """Singleton in charge of providing a single shared Postgres connection."""

    _connection: ClassVar[PGConnection | None] = None

    @classmethod
    def get_connection(cls) -> PGConnection:
        if cls._connection is None or cls._connection.closed:
            ensure_database_exists()
            cls._connection = psycopg2.connect(POSTGRES_DSN)
            cls._connection.autocommit = True
        return cls._connection

    @classmethod
    def reset(cls) -> None:
        if cls._connection and not cls._connection.closed:
            cls._connection.close()
        cls._connection = None


def get_connection() -> PGConnection:
    return PostgresConnectionSingleton.get_connection()


def _ensure_schema(cur) -> None:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tutorial_recipes'
        ORDER BY ordinal_position
        """
    )
    columns = [row[0] for row in cur.fetchall()]
    if columns == EXPECTED_COLUMNS:
        return
    cur.execute("DROP TABLE IF EXISTS tutorial_recipes")
    cur.execute(CREATE_TABLE_SQL)


def initialize_table() -> None:
    conn = get_connection()
    with conn.cursor() as cur:
        _ensure_schema(cur)


def insert_sample_data(samples: Iterable[tuple[str, float, float, float, float, float, float, float, float, float]]) -> None:
    conn = get_connection()
    with conn.cursor() as cur:
        for sample in samples:
            cur.execute(INSERT_SQL, sample)


def fetch_all_recipes() -> list[Recipe]:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(SELECT_ALL_SQL)
        rows = cur.fetchall()
    return [Recipe(*row) for row in rows]


def ensure_seed_data() -> None:
    # Ensure the target database exists before trying to create tables inside it
    ensure_database_exists()
    initialize_table()
    if not fetch_all_recipes():
        insert_sample_data(SEED_RECIPES)


if __name__ == "__main__":
    ensure_seed_data()
    for recipe in fetch_all_recipes():
        print(recipe)
