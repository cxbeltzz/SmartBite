import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

try:
    import psycopg2
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None


def scaling(dataframe):
    scaler = StandardScaler()
    prep_data = scaler.fit_transform(dataframe.iloc[:, 6:15].to_numpy())
    return prep_data, scaler


def nn_predictor(prep_data):
    neigh = NearestNeighbors(metric="cosine", algorithm="brute")
    neigh.fit(prep_data)
    return neigh


def build_pipeline(neigh, scaler, params):
    transformer = FunctionTransformer(neigh.kneighbors, kw_args=params)
    pipeline = Pipeline([("std_scaler", scaler), ("NN", transformer)])
    return pipeline


def extract_data(dataframe, ingredients):
    extracted_data = dataframe.copy()
    extracted_data = extract_ingredient_filtered_data(extracted_data, ingredients)
    return extracted_data


def extract_ingredient_filtered_data(dataframe, ingredients):
    extracted_data = dataframe.copy()
    regex_string = "".join(map(lambda x: f"(?=.*{x})", ingredients))
    extracted_data = extracted_data[
        extracted_data["RecipeIngredientParts"].str.contains(
            regex_string, regex=True, flags=re.IGNORECASE
        )
    ]
    return extracted_data


def apply_pipeline(pipeline, _input, extracted_data):
    _input = np.array(_input).reshape(1, -1)
    return extracted_data.iloc[pipeline.transform(_input)[0]]


def recommend(
    dataframe,
    _input,
    ingredients=[],
    params={"n_neighbors": 5, "return_distance": False},
):
    extracted_data = extract_data(dataframe, ingredients)
    if extracted_data.shape[0] >= params["n_neighbors"]:
        prep_data, scaler = scaling(extracted_data)
        neigh = nn_predictor(prep_data)
        pipeline = build_pipeline(neigh, scaler, params)
        return apply_pipeline(pipeline, _input, extracted_data)
    else:
        return None


def extract_quoted_strings(s):
    # Find all the strings inside double quotes
    strings = re.findall(r'"([^"]*)"', s)
    # Join the strings with 'and'
    return strings


def output_recommended_recipes(dataframe):
    if dataframe is not None:
        output = dataframe.copy()
        output = output.to_dict("records")
        for recipe in output:
            recipe["RecipeIngredientParts"] = extract_quoted_strings(
                recipe["RecipeIngredientParts"]
            )
            recipe["RecipeInstructions"] = extract_quoted_strings(
                recipe["RecipeInstructions"]
            )
            if "RecipeImages" in recipe:
                if isinstance(recipe["RecipeImages"], str):
                    recipe["RecipeImages"] = extract_quoted_strings(
                        recipe["RecipeImages"]
                    )
                else:
                    recipe["RecipeImages"] = recipe["RecipeImages"] or []
            else:
                recipe["RecipeImages"] = []
    else:
        output = None
    return output


def _format_as_r_vector(items):
    """Format a list of values as the original c("a", "b") literal."""
    if not items:
        return "c()"
    safe_items = [item.replace('"', '\\"') for item in items]
    return "c(" + ", ".join(f'"{value}"' for value in safe_items) + ")"


def _load_dataframe_from_connection(connection):
    recipes = pd.read_sql_query(
        """
        SELECT
            recipe_id AS "RecipeId",
            name AS "Name",
            cook_time AS "CookTime",
            prep_time AS "PrepTime",
            total_time AS "TotalTime",
            calories AS "Calories",
            fat_content AS "FatContent",
            saturated_fat_content AS "SaturatedFatContent",
            cholesterol_content AS "CholesterolContent",
            sodium_content AS "SodiumContent",
            carbohydrate_content AS "CarbohydrateContent",
            fiber_content AS "FiberContent",
            sugar_content AS "SugarContent",
            protein_content AS "ProteinContent"
        FROM recipes
        ORDER BY recipe_id
        """,
        connection,
    )
    ingredients = pd.read_sql_query(
        """
        SELECT ri.recipe_id, ri.position, i.name
        FROM recipe_ingredients AS ri
        INNER JOIN ingredients AS i ON i.ingredient_id = ri.ingredient_id
        ORDER BY ri.recipe_id, ri.position
        """,
        connection,
    )
    instructions = pd.read_sql_query(
        """
        SELECT recipe_id, step_order, instruction
        FROM instructions
        ORDER BY recipe_id, step_order
        """,
        connection,
    )
    images = pd.read_sql_query(
        """
        SELECT recipe_id, position, url
        FROM recipe_images
        ORDER BY recipe_id, position
        """,
        connection,
    )

    ingredient_groups = (
        ingredients.groupby("recipe_id")["name"].apply(list).to_dict()
        if not ingredients.empty
        else {}
    )
    instruction_groups = (
        instructions.groupby("recipe_id")["instruction"].apply(list).to_dict()
        if not instructions.empty
        else {}
    )
    image_groups = (
        images.groupby("recipe_id")["url"].apply(list).to_dict()
        if not images.empty
        else {}
    )

    recipes["RecipeIngredientParts"] = recipes["RecipeId"].map(
        lambda recipe_id: _format_as_r_vector(ingredient_groups.get(recipe_id, []))
    )
    recipes["RecipeInstructions"] = recipes["RecipeId"].map(
        lambda recipe_id: _format_as_r_vector(instruction_groups.get(recipe_id, []))
    )
    recipes["RecipeImages"] = recipes["RecipeId"].map(
        lambda recipe_id: _format_as_r_vector(image_groups.get(recipe_id, []))
    )

    ordered_columns = [
        "RecipeId",
        "Name",
        "CookTime",
        "PrepTime",
        "TotalTime",
        "RecipeIngredientParts",
        "Calories",
        "FatContent",
        "SaturatedFatContent",
        "CholesterolContent",
        "SodiumContent",
        "CarbohydrateContent",
        "FiberContent",
        "SugarContent",
        "ProteinContent",
        "RecipeInstructions",
        "RecipeImages",
    ]
    return recipes[ordered_columns]


def load_dataframe_from_postgres(db_url):
    """Retrieve the denormalized dataframe from a PostgreSQL database."""
    if psycopg2 is None:
        raise ImportError(
            "psycopg2 is required to load data from PostgreSQL. Install it with 'pip install psycopg2-binary'."
        )

    with psycopg2.connect(db_url) as connection:
        return _load_dataframe_from_connection(connection)


def load_dataframe_from_db(db_url):
    """Compatibility wrapper that delegates to the PostgreSQL loader."""
    return load_dataframe_from_postgres(db_url)


def recommend_from_postgres(db_url, _input, ingredients=None, params=None):
    dataframe = load_dataframe_from_postgres(db_url)
    selected_ingredients = ingredients if ingredients is not None else []
    model_params = (
        params if params is not None else {"n_neighbors": 5, "return_distance": False}
    )
    return recommend(dataframe, _input, selected_ingredients, model_params)


def recommend_from_db(db_url, _input, ingredients=None, params=None):
    """Compatibility wrapper that delegates to the PostgreSQL recommender."""
    return recommend_from_postgres(db_url, _input, ingredients, params)
