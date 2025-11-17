"""
TEST: recomendaciones_por_comida

Objetivo
--------
Garantizar que `recommend_meals` construye la rejilla de comidas que usa la
UI: debe solicitar datos al modelo, deduplicar recetas y asignar exactamente
`RECIPES_PER_MEAL` por cada comida solicitada.

Casos límite
------------
- `meals_per_day=2` -> usa etiquetas `breakfast` y `lunch`
- Suficientes recetas únicas -> todas las ranuras se llenan
- Duplicados iniciales -> se eliminan antes de repartir
"""

import unittest
from unittest.mock import patch

import app


class TestAppRecommendMeals(unittest.TestCase):
	def test_assigns_full_meal_slots_with_unique_recipes(self):
		sample_recipes = [
			{"RecipeId": 1, "Name": "Duplicate"},
			{"RecipeId": 1, "Name": "Duplicate"},  # duplicate should be dropped
		]
		sample_recipes.extend(
			{"RecipeId": idx, "Name": f"Recipe {idx}"}
			for idx in range(2, 2 + app.RECIPES_PER_MEAL * 2)
		)

		with (
			patch("app._get_dataframe", return_value="fake_df") as mock_get_df,
			patch("app.model.recommend", return_value="raw_df") as mock_recommend,
			patch("app.model.output_recommended_recipes", return_value=sample_recipes),
		):
			grouped = app.recommend_meals(calories_per_meal=600, meals_per_day=2)

		mock_get_df.assert_called_once()
		mock_recommend.assert_called_once()
		self.assertIs(mock_recommend.call_args.args[0], "fake_df")

		expected_keys = list(app.MEAL_LABELS.keys())[:2]
		self.assertEqual(list(grouped.keys()), expected_keys)
		self.assertTrue(
			all(len(recipes) == app.RECIPES_PER_MEAL for recipes in grouped.values())
		)

		all_ids = [recipe["RecipeId"] for recipes in grouped.values() for recipe in recipes]
		self.assertEqual(len(all_ids), len(set(all_ids)))


if __name__ == "__main__":
	unittest.main()
