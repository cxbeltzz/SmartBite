import os
from dataclasses import dataclass
from typing import Iterable

import psycopg2
from psycopg2.extensions import connection as PGConnection



POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/TUTORIAL_DEMO")

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


def get_connection() -> PGConnection:
    return psycopg2.connect(POSTGRES_DSN)


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
    with get_connection() as conn:
        with conn.cursor() as cur:
            _ensure_schema(cur)


def insert_sample_data(samples: Iterable[tuple[str, float, float, float, float, float, float, float, float, float]]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for sample in samples:
                cur.execute(INSERT_SQL, sample)


def fetch_all_recipes() -> list[Recipe]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT_ALL_SQL)
            rows = cur.fetchall()
    return [Recipe(*row) for row in rows]


def ensure_seed_data() -> None:
    initialize_table()
    if not fetch_all_recipes():
        insert_sample_data(SEED_RECIPES)


if __name__ == "__main__":
    ensure_seed_data()
    for recipe in fetch_all_recipes():
        print(recipe)
