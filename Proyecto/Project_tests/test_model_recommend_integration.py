"""
TEST: recomendacion_integral

Objetivo
--------
Validar que `recommend` genera vecinos cuando existen suficientes recetas y
que el resultado mantiene la cantidad solicitada en `n_neighbors`.

Casos límite
------------
- DataFrame con más recetas que vecinos -> respuesta válida (DataFrame)
- Vector alineado con la primera receta -> dicha receta aparece en el top
- Parámetros personalizados (`n_neighbors`) -> controla tamaño del resultado
"""

import unittest

import pandas as pd

import model


def _make_dataset(num_rows=6):
    base = {
        "RecipeId": list(range(1, num_rows + 1)),
        "Name": [f"Recipe {idx}" for idx in range(1, num_rows + 1)],
        "CookTime": [10 + idx for idx in range(num_rows)],
        "PrepTime": [5 + idx for idx in range(num_rows)],
        "TotalTime": [15 + idx for idx in range(num_rows)],
        "RecipeIngredientParts": ["chicken, rice" for _ in range(num_rows)],
        "Calories": [400 + idx * 50 for idx in range(num_rows)],
        "FatContent": [10 + idx * 2 for idx in range(num_rows)],
        "SaturatedFatContent": [3 + idx * 1.5 for idx in range(num_rows)],
        "CholesterolContent": [30 + idx * 4 for idx in range(num_rows)],
        "SodiumContent": [400 + idx * 60 for idx in range(num_rows)],
        "CarbohydrateContent": [30 + idx * 5 for idx in range(num_rows)],
        "FiberContent": [5 + idx for idx in range(num_rows)],
        "SugarContent": [10 + idx * 2 for idx in range(num_rows)],
        "ProteinContent": [25 + idx * 3 for idx in range(num_rows)],
    }
    return pd.DataFrame(base)


class TestModelRecommendIntegration(unittest.TestCase):
    def test_recommend_returns_requested_neighbors(self):
        dataframe = _make_dataset(6)
        vector = [
            dataframe.loc[0, "Calories"],
            dataframe.loc[0, "FatContent"],
            dataframe.loc[0, "SaturatedFatContent"],
            dataframe.loc[0, "CholesterolContent"],
            dataframe.loc[0, "SodiumContent"],
            dataframe.loc[0, "CarbohydrateContent"],
            dataframe.loc[0, "FiberContent"],
            dataframe.loc[0, "SugarContent"],
            dataframe.loc[0, "ProteinContent"],
        ]

        params = {"n_neighbors": 3, "return_distance": False}
        result = model.recommend(dataframe, vector, params=params)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertIn(result.iloc[0]["RecipeId"], dataframe["RecipeId"].tolist())
        self.assertIn(1, result["RecipeId"].tolist())


if __name__ == "__main__":
    unittest.main()
