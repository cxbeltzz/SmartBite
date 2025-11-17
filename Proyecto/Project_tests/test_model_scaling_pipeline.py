"""
TEST: vector_escalado

Objetivo
--------
Comprobar que `scaling` normaliza los atributos nutricionales y entrega un
`StandardScaler` utilizable posteriormente en el pipeline de recomendación.

Casos límite
------------
- Múltiples recetas con diferentes magnitudes -> medias aproximadas a 0
- Varianzas no nulas -> evita divisiones por cero en el escalador
- Número de columnas esperado (9 features nutricionales) -> mantiene forma
"""

import unittest

import numpy as np
import pandas as pd

import model


FEATURE_COLUMNS = [
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
]


class TestModelScalingPipeline(unittest.TestCase):
    def test_scaling_returns_zero_mean_features(self):
        dataframe = pd.DataFrame(
            {
                "RecipeId": [1, 2, 3],
                "Name": ["R1", "R2", "R3"],
                "CookTime": [10, 12, 8],
                "PrepTime": [5, 6, 4],
                "TotalTime": [15, 18, 12],
                "RecipeIngredientParts": ["a", "b", "c"],
                "Calories": [400, 650, 500],
                "FatContent": [10, 20, 15],
                "SaturatedFatContent": [3, 8, 5],
                "CholesterolContent": [30, 60, 45],
                "SodiumContent": [400, 900, 650],
                "CarbohydrateContent": [30, 70, 55],
                "FiberContent": [5, 8, 7],
                "SugarContent": [10, 25, 20],
                "ProteinContent": [25, 40, 30],
            }
        )[FEATURE_COLUMNS]

        prep_data, scaler = model.scaling(dataframe)

        self.assertEqual(prep_data.shape, (3, 9))
        self.assertTrue(np.allclose(prep_data.mean(axis=0), 0.0, atol=1e-7))
        self.assertTrue(np.all(scaler.scale_ > 0))


if __name__ == "__main__":
    unittest.main()
