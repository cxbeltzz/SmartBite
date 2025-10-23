# Hola Mundo tutorial: Flask + PostgreSQL + Tailwind
from typing import Dict, List, Optional

from flask import Flask, render_template

from database import Recipe, ensure_seed_data, fetch_all_recipes


FEATURE_LABELS: List[str] = [
    "Calories (kcal)",
    "Fat (g)",
    "Saturated Fat (g)",
    "Cholesterol (mg)",
    "Sodium (mg)",
    "Carbohydrates (g)",
    "Fiber (g)",
    "Sugar (g)",
    "Protein (g)",
]


CARD_LAYOUTS = [
    ("breakfast", "Sample Breakfast"),
    ("lunch", "Sample Lunch"),
    ("dinner", "Sample Dinner"),
]


app = Flask(__name__)

ensure_seed_data()


def _build_pairs(recipe: Recipe) -> List[tuple[str, float]]:
    values = [
        recipe.calories,
        recipe.fat,
        recipe.saturated_fat,
        recipe.cholesterol,
        recipe.sodium,
        recipe.carbohydrates,
        recipe.fiber,
        recipe.sugar,
        recipe.protein,
    ]
    return list(zip(FEATURE_LABELS, values))


@app.route("/")
def index():
    recipes = fetch_all_recipes()
    cards: Dict[str, dict] = {}
    for idx, (key, title) in enumerate(CARD_LAYOUTS):
        recipe: Optional[Recipe] = recipes[idx] if idx < len(recipes) else None
        cards[key] = {
            "title": title,
            "pairs": _build_pairs(recipe) if recipe else [],
            "recipe": recipe,
        }
    return render_template(
        "index.html",
        recipes=recipes,
        cards=cards,
    )


if __name__ == "__main__":
    app.run(debug=True)
