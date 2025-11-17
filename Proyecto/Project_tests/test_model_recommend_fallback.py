"""
TEST: recomendador_sin_vecinos

Objetivo
--------
Verificar que `recommend` retorna `None` cuando no hay suficientes recetas
para satisfacer `n_neighbors`, evitando ejecutar el pipeline con datos
insuficientes.

Casos límite
------------
- DataFrame con menos recetas que `n_neighbors` -> `None`
- Ingredientes opcionales vacíos -> no afectan el resultado
- Vector de nutrientes válido con 9 elementos -> requisito para la llamada
"""

import unittest

import pandas as pd

import model


class TestModelRecommendFallback(unittest.TestCase):
    def test_recommend_returns_none_when_not_enough_neighbors(self):
        dataframe = pd.DataFrame(
            {
                "RecipeId": [1, 2],
                "Name": ["Recipe 1", "Recipe 2"],
                "CookTime": [10, 12],
                "PrepTime": [5, 6],
                "TotalTime": [15, 18],
                "RecipeIngredientParts": ["milk, egg", "egg"],
                "Calories": [200, 210],
                "FatContent": [10, 11],
                "SaturatedFatContent": [3, 3.1],
                "CholesterolContent": [30, 35],
                "SodiumContent": [200, 220],
                "CarbohydrateContent": [20, 22],
                "FiberContent": [5, 6],
                "SugarContent": [8, 7],
                "ProteinContent": [15, 14],
            }
        )

        vector = [500, 20, 7, 50, 400, 60, 10, 20, 25]
        params = {"n_neighbors": 5, "return_distance": False}

        result = model.recommend(dataframe, vector, params=params)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
