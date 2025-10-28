import argparse
import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import psycopg2
    from psycopg2.extensions import connection as PGConnection
except ImportError as exc:
    raise ImportError(
        "psycopg2"
    ) from exc


LIST_ITEM_PATTERN = re.compile(r'"([^\"]*)"')


def parse_quoted_list(raw_value: Optional[str]) -> List[str]:
    """Return the list of quoted strings inside an R-style c("a", "b") literal."""
    if not raw_value:
        return []
    matches = LIST_ITEM_PATTERN.findall(raw_value)
    # Normalize whitespace to keep lookups consistent
    return [item.strip() for item in matches if item.strip()]


def to_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def create_schema(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            recipe_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            cook_time TEXT,
            prep_time TEXT,
            total_time TEXT,
            calories DOUBLE PRECISION,
            fat_content DOUBLE PRECISION,
            saturated_fat_content DOUBLE PRECISION,
            cholesterol_content DOUBLE PRECISION,
            sodium_content DOUBLE PRECISION,
            carbohydrate_content DOUBLE PRECISION,
            fiber_content DOUBLE PRECISION,
            sugar_content DOUBLE PRECISION,
            protein_content DOUBLE PRECISION
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            recipe_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            PRIMARY KEY (recipe_id, position),
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS instructions (
            recipe_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            instruction TEXT NOT NULL,
            PRIMARY KEY (recipe_id, step_order),
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
        )
        """
    )


def clear_existing_data(cursor) -> None:
    cursor.execute("TRUNCATE TABLE recipe_ingredients RESTART IDENTITY CASCADE")
    cursor.execute("TRUNCATE TABLE instructions RESTART IDENTITY CASCADE")
    cursor.execute("TRUNCATE TABLE ingredients RESTART IDENTITY CASCADE")
    cursor.execute("TRUNCATE TABLE recipes RESTART IDENTITY CASCADE")


def upsert_ingredient(cursor, cache: Dict[str, int], name: str) -> int:
    cached = cache.get(name)
    if cached is not None:
        return cached
    cursor.execute(
        """
        INSERT INTO ingredients(name)
        VALUES (%s)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING ingredient_id
        """,
        (name,),
    )
    ingredient_id = cursor.fetchone()[0]
    cache[name] = ingredient_id
    return ingredient_id


def load_rows(csv_path: Path) -> Iterable[dict]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def populate_database(csv_path: Path, dsn: str) -> None:
    connection: PGConnection = psycopg2.connect(dsn)
    try:
        with connection:
            with connection.cursor() as cursor:
                create_schema(cursor)
        with connection:
            with connection.cursor() as cursor:
                clear_existing_data(cursor)
        ingredient_cache: Dict[str, int] = {}
        with connection:
            with connection.cursor() as cursor:
                for row in load_rows(csv_path):
                    recipe_id = int(row["RecipeId"])
                    cursor.execute(
                        """
                        INSERT INTO recipes(
                            recipe_id, name, cook_time, prep_time, total_time,
                            calories, fat_content, saturated_fat_content,
                            cholesterol_content, sodium_content, carbohydrate_content,
                            fiber_content, sugar_content, protein_content
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (recipe_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            cook_time = EXCLUDED.cook_time,
                            prep_time = EXCLUDED.prep_time,
                            total_time = EXCLUDED.total_time,
                            calories = EXCLUDED.calories,
                            fat_content = EXCLUDED.fat_content,
                            saturated_fat_content = EXCLUDED.saturated_fat_content,
                            cholesterol_content = EXCLUDED.cholesterol_content,
                            sodium_content = EXCLUDED.sodium_content,
                            carbohydrate_content = EXCLUDED.carbohydrate_content,
                            fiber_content = EXCLUDED.fiber_content,
                            sugar_content = EXCLUDED.sugar_content,
                            protein_content = EXCLUDED.protein_content
                        """,
                        (
                            recipe_id,
                            row.get("Name"),
                            row.get("CookTime"),
                            row.get("PrepTime"),
                            row.get("TotalTime"),
                            to_float(row.get("Calories")),
                            to_float(row.get("FatContent")),
                            to_float(row.get("SaturatedFatContent")),
                            to_float(row.get("CholesterolContent")),
                            to_float(row.get("SodiumContent")),
                            to_float(row.get("CarbohydrateContent")),
                            to_float(row.get("FiberContent")),
                            to_float(row.get("SugarContent")),
                            to_float(row.get("ProteinContent")),
                        ),
                    )
                    ingredients = parse_quoted_list(row.get("RecipeIngredientParts"))
                    for position, ingredient in enumerate(ingredients):
                        ingredient_id = upsert_ingredient(cursor, ingredient_cache, ingredient)
                        cursor.execute(
                            """
                            INSERT INTO recipe_ingredients(recipe_id, position, ingredient_id)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (recipe_id, position) DO UPDATE SET ingredient_id = EXCLUDED.ingredient_id
                            """,
                            (recipe_id, position, ingredient_id),
                        )
                    instructions = parse_quoted_list(row.get("RecipeInstructions"))
                    for step_order, instruction in enumerate(instructions):
                        cursor.execute(
                            """
                            INSERT INTO instructions(recipe_id, step_order, instruction)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (recipe_id, step_order) DO UPDATE SET instruction = EXCLUDED.instruction
                            """,
                            (recipe_id, step_order, instruction),
                        )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize recipe dataset into a PostgreSQL database")
    parser.add_argument("csv_path", type=Path, help="Path to the raw CSV dataset")
    parser.add_argument(
        "dsn",
        help="PostgreSQL DSN, e.g. postgresql://user:password@host:5432/database",
    )
    args = parser.parse_args()
    populate_database(args.csv_path, args.dsn)


if __name__ == "__main__":
    main()
