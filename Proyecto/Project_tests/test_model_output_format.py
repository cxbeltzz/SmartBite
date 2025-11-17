"""
TEST: recetas_formateadas

Objetivo
--------
Comprobar que `output_recommended_recipes` transforma los campos en formato
`c("...")` a listas de Python y normaliza los valores faltantes en las
imágenes.

Casos límite
------------
- Ingredientes/instrucciones en formato R -> lista de strings
- Campo `RecipeImages` como `None` -> lista vacía
- Cadena con comillas escapadas -> se preservan en la salida
"""

import unittest

import pandas as pd

import model


class TestModelOutputFormat(unittest.TestCase):
    def test_output_recommended_recipes_formats_fields(self):
        dataframe = pd.DataFrame(
            {
                "RecipeId": [1, 2],
                "Name": ["Omelette", "Toast"],
                "RecipeIngredientParts": [
                    'c("egg", "cheese")',
                    'c("bread")',
                ],
                "RecipeInstructions": [
                    'c("Beat eggs", "Cook")',
                    'c("Toast bread")',
                ],
                "RecipeImages": [
                    'c("https://img/omelette.png")',
                    None,
                ],
            }
        )

        output = model.output_recommended_recipes(dataframe)

        self.assertIsInstance(output, list)
        self.assertEqual(output[0]["RecipeIngredientParts"], ["egg", "cheese"])
        self.assertEqual(output[0]["RecipeInstructions"], ["Beat eggs", "Cook"])
        self.assertEqual(output[0]["RecipeImages"], ["https://img/omelette.png"])
        self.assertEqual(output[1]["RecipeImages"], [])


if __name__ == "__main__":
    unittest.main()
