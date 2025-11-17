"""
TEST: ingredientes_filtrados

Objetivo
--------
Asegurar que `extract_ingredient_filtered_data` solo devuelva recetas que
contienen todos los ingredientes buscados sin importar mayúsculas/minúsculas.

Casos límite
------------
- Coincidencia exacta de todos los ingredientes -> válido
- Ingrediente faltante en la receta -> excluido
- Coincidencia con diferencias de capitalización -> válido
"""

import unittest

import pandas as pd

import model


class TestModelExtractFilter(unittest.TestCase):
    def test_extract_ingredient_filtered_data_case_insensitive(self):
        dataframe = pd.DataFrame(
            {
                "RecipeId": [1, 2],
                "RecipeIngredientParts": [
                    "Chicken breast, GARLIC, paprika",
                    "Chicken breast, paprika",
                ],
            }
        )

        filtered = model.extract_ingredient_filtered_data(
            dataframe, ["chicken", "garlic"]
        )

        self.assertEqual(filtered.shape[0], 1)
        self.assertEqual(filtered.iloc[0]["RecipeId"], 1)


if __name__ == "__main__":
    unittest.main()
