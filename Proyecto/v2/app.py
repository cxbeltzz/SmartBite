import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from flask import Flask, render_template, request

import model

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "mmmm")

app = Flask(__name__)

_dataframe_cache = None


ACTIVITY_LEVELS: Dict[str, Tuple[str, float]] = {
    "sedentary": ("Little/no exercise", 1.2),
    "light": ("Light exercise (1-2 days/wk)", 1.375),
    "moderate": ("Moderate exercise (3-5 days/wk)", 1.55),
    "active": ("Active (6-7 days/wk)", 1.725),
    "extra": ("Extra active (very physical job)", 1.9),
}
ACTIVITY_ORDER = list(ACTIVITY_LEVELS.keys())

WEIGHT_PLANS: Dict[str, Tuple[str, int, float]] = {
    "maintain": ("Maintain weight", 0, 0.0),
    "mild": ("Mild weight loss", -250, -0.25),
    "loss": ("Weight loss", -500, -0.5),
    "extreme": ("Extreme weight loss", -1000, -1.0),
}

MACRO_SPLIT = {
    "fat_pct": 0.30,
    "carb_pct": 0.45,
    "protein_pct": 0.25,
}

MEAL_LABELS: Dict[str, str] = {
    "breakfast": "Desayuno",
    "lunch": "Almuerzo",
    "dinner": "Cena",
}


RECIPES_PER_MEAL = 5

CUSTOM_NUTRIENT_FIELDS = [
    {
        "name": "calories",
        "label": "Calorías",
        "min": 0,
        "max": 2000,
        "step": 10,
        "unit": "kcal",
        "precision": 0,
    },
    {
        "name": "fat",
        "label": "Grasas totales",
        "min": 0,
        "max": 100,
        "step": 1,
        "unit": "g",
        "precision": 1,
    },
    {
        "name": "saturated_fat",
        "label": "Grasas saturadas",
        "min": 0,
        "max": 60,
        "step": 1,
        "unit": "g",
        "precision": 1,
    },
    {
        "name": "cholesterol",
        "label": "Colesterol",
        "min": 0,
        "max": 400,
        "step": 5,
        "unit": "mg",
        "precision": 0,
    },
    {
        "name": "sodium",
        "label": "Sodio",
        "min": 0,
        "max": 2500,
        "step": 10,
        "unit": "mg",
        "precision": 0,
    },
    {
        "name": "carbs",
        "label": "Carbohidratos",
        "min": 0,
        "max": 325,
        "step": 5,
        "unit": "g",
        "precision": 1,
    },
    {
        "name": "fiber",
        "label": "Fibra",
        "min": 0,
        "max": 60,
        "step": 1,
        "unit": "g",
        "precision": 1,
    },
    {
        "name": "sugar",
        "label": "Azúcares",
        "min": 0,
        "max": 80,
        "step": 1,
        "unit": "g",
        "precision": 1,
    },
    {
        "name": "protein",
        "label": "Proteína",
        "min": 0,
        "max": 120,
        "step": 1,
        "unit": "g",
        "precision": 1,
    },
]


@dataclass
class UserInput:
    age: int
    height_cm: float
    weight_kg: float
    gender: str
    activity: str
    plan: str
    meals_per_day: int


def _get_dataframe():
    global _dataframe_cache
    if _dataframe_cache is None:
        _dataframe_cache = model.load_dataframe_from_postgres(POSTGRES_DSN)
    return _dataframe_cache


def calculate_bmi(weight_kg: float, height_cm: float) -> Tuple[float, str]:
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        status = "Underweight"
    elif bmi < 25:
        status = "Normal"
    elif bmi < 30:
        status = "Overweight"
    else:
        status = "Obese"
    return round(bmi, 2), status


def calculate_tdee(user: UserInput) -> float:
    sex_constant = 5 if user.gender == "male" else -161
    bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + sex_constant
    activity_factor = ACTIVITY_LEVELS[user.activity][1]
    return bmr * activity_factor


def plan_targets(tdee: float) -> Dict[str, Dict[str, float]]:
    targets: Dict[str, Dict[str, float]] = {}
    for plan_key, (label, adjustment, delta_kg) in WEIGHT_PLANS.items():
        calories = max(tdee + adjustment, 1200)
        targets[plan_key] = {
            "label": label,
            "calories": round(calories),
            "delta_kg": delta_kg,
        }
    return targets


def build_nutrient_vector(calories_per_meal: float) -> List[float]:
    fat_grams = max(calories_per_meal * MACRO_SPLIT["fat_pct"] / 9.0, 1.0)
    sat_fat = fat_grams * 0.35
    cholesterol = 300 / 3  # aim for <300 mg per day
    sodium = 2300 / 3
    carbs = max(calories_per_meal * MACRO_SPLIT["carb_pct"] / 4.0, 1.0)
    fiber = 30 / 3
    sugar = 40 / 3
    protein = max(calories_per_meal * MACRO_SPLIT["protein_pct"] / 4.0, 1.0)
    return [
        calories_per_meal,
        fat_grams,
        sat_fat,
        cholesterol,
        sodium,
        carbs,
        fiber,
        sugar,
        protein,
    ]


def compute_macro_targets(calories: float) -> Dict[str, int]:
    """Return rounded macro targets for a calorie goal."""
    total_calories = round(calories)
    fat = round(calories * MACRO_SPLIT["fat_pct"] / 9.0)
    carbs = round(calories * MACRO_SPLIT["carb_pct"] / 4.0)
    protein = round(calories * MACRO_SPLIT["protein_pct"] / 4.0)
    return {
        "calories": total_calories,
        "fat": fat,
        "carbs": carbs,
        "protein": protein,
    }


def _build_meal_keys(meals_per_day: int) -> List[str]:
    base_sequence = list(MEAL_LABELS.keys())
    keys: List[str] = []
    for idx in range(max(meals_per_day, 1)):
        if idx < len(base_sequence):
            keys.append(base_sequence[idx])
        else:
            keys.append(f"meal_{idx + 1}")
    return keys


def recommend_meals(calories_per_meal: float, meals_per_day: int) -> Dict[str, List[dict]]:
    vector = build_nutrient_vector(calories_per_meal)
    dataframe = _get_dataframe()
    meal_keys = _build_meal_keys(meals_per_day)
    recipes_needed = max(len(meal_keys) * RECIPES_PER_MEAL, RECIPES_PER_MEAL)
    # Request extra neighbors to preserve variety after filtering duplicates.
    params = {"n_neighbors": max(recipes_needed * 2, 30), "return_distance": False}
    recommendations = model.recommend(dataframe, vector, params=params)
    grouped: "OrderedDict[str, List[dict]]" = OrderedDict()
    if recommendations is None:
        for key in meal_keys:
            grouped[key] = []
        return grouped

    records = model.output_recommended_recipes(recommendations)
    seen_identifiers = set()
    unique_records: List[dict] = []
    for record in records:
        identifier = (
            record.get("RecipeId")
            or record.get("RecipeID")
            or record.get("id")
            or record.get("Name")
        )
        if identifier in seen_identifiers:
            continue
        seen_identifiers.add(identifier)
        unique_records.append(record)
        if len(unique_records) >= recipes_needed:
            break

    for idx, key in enumerate(meal_keys):
        start = idx * RECIPES_PER_MEAL
        end = start + RECIPES_PER_MEAL
        grouped[key] = unique_records[start:end]

    return grouped


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
    composition_payload = {"active": False}
    user_values = {
        "age": 22,
        "height_cm": 171,
        "weight_kg": 65,
        "gender": "male",
        "activity": "moderate",
        "plan": "maintain",
        "meals_per_day": 3,
    }
    if request.method == "POST":
        try:
            user_values = {
                "age": int(request.form.get("age", 22)),
                "height_cm": float(request.form.get("height_cm", 171)),
                "weight_kg": float(request.form.get("weight_kg", 65)),
                "gender": request.form.get("gender", "male"),
                "activity_index": int(request.form.get("activity_index", ACTIVITY_ORDER.index("moderate"))),
                "plan": request.form.get("plan", "maintain"),
                "meals_per_day": int(request.form.get("meals_per_day", 3)),
            }
            activity_index = max(0, min(user_values["activity_index"], len(ACTIVITY_ORDER) - 1))
            activity_key = ACTIVITY_ORDER[activity_index]
            user_values["activity"] = activity_key
            user = UserInput(
                age=user_values["age"],
                height_cm=user_values["height_cm"],
                weight_kg=user_values["weight_kg"],
                gender=user_values["gender"],
                activity=activity_key,
                plan=user_values["plan"],
                meals_per_day=user_values["meals_per_day"],
            )
            _get_dataframe()  # ensure cache
            bmi, bmi_status = calculate_bmi(user.weight_kg, user.height_cm)
            tdee = calculate_tdee(user)
            targets = plan_targets(tdee)
            selected_plan = targets[user.plan]
            calories_per_meal = selected_plan["calories"] / max(user.meals_per_day, 1)
            recommendations = recommend_meals(calories_per_meal, user.meals_per_day)
            result = {
                "bmi": bmi,
                "bmi_status": bmi_status,
                "tdee": round(tdee),
                "targets": targets,
                "selected_plan_key": user.plan,
                "meals_per_day": user.meals_per_day,
                "recommendations": recommendations,
            }
            result["selected_plan"] = selected_plan
            result["user"] = user
            result["macro_total"] = compute_macro_targets(selected_plan["calories"])
            result["macro_per_meal"] = compute_macro_targets(calories_per_meal)
            flat_recommendations: List[dict] = []
            meal_labels = {}
            meal_order = list(recommendations.keys())
            for index, (meal_key, recipes) in enumerate(recommendations.items()):
                label = MEAL_LABELS.get(meal_key, f"Comida {index + 1}")
                meal_labels[meal_key] = label
                for recipe in recipes:
                    enriched = dict(recipe)
                    enriched["meal_key"] = meal_key
                    enriched["meal_label"] = label
                    flat_recommendations.append(enriched)
            result["meal_labels"] = meal_labels
            result["flat_recommendations"] = flat_recommendations
            result["meal_order"] = meal_order
            composition_payload = {
                "active": True,
                "meal_labels": meal_labels,
                "recommendations": recommendations,
                "meal_order": meal_order,
                "plan_calories": selected_plan["calories"],
                "macro_targets_day": result["macro_total"],
                "macro_targets_meal": result["macro_per_meal"],
            }
        except Exception as exc:  # pylint: disable=broad-except
            error = str(exc)
    return render_template(
        "index.html",
        activities=ACTIVITY_LEVELS,
        activity_order=ACTIVITY_ORDER,
        plans=WEIGHT_PLANS,
        defaults=user_values,
        activity_index=ACTIVITY_ORDER.index(user_values.get("activity", "moderate")),
        error=error,
        result=result,
        composer_payload=composition_payload,
    )


def _build_custom_vector(values: Dict[str, float]) -> List[float]:
    return [
        values["calories"],
        values["fat"],
        values["saturated_fat"],
        values["cholesterol"],
        values["sodium"],
        values["carbs"],
        values["fiber"],
        values["sugar"],
        values["protein"],
    ]


@app.route("/personalizado", methods=["GET", "POST"])
def custom_recommendations():
    defaults = {
        "calories": 550.0,
        "fat": 25.0,
        "saturated_fat": 10.0,
        "cholesterol": 50.0,
        "sodium": 800.0,
        "carbs": 80.0,
        "fiber": 10.0,
        "sugar": 20.0,
        "protein": 25.0,
    }
    recommendations: List[dict] = []
    error = None
    info_message = None
    ingredients_input = ""
    recommendation_count = 5

    if request.method == "POST":
        try:
            for field in CUSTOM_NUTRIENT_FIELDS:
                raw_value = request.form.get(field["name"], defaults[field["name"]])
                defaults[field["name"]] = max(field["min"], min(field["max"], float(raw_value)))

            recommendation_count = int(request.form.get("recommendation_count", recommendation_count))
            recommendation_count = max(1, min(20, recommendation_count))

            ingredients_input = request.form.get("ingredients", "").strip()
            ingredient_terms = [token.strip() for token in ingredients_input.split(",") if token.strip()]

            nutrient_vector = _build_custom_vector(defaults)
            dataframe = _get_dataframe()
            params = {"n_neighbors": max(recommendation_count, 1), "return_distance": False}
            raw_results = model.recommend(dataframe, nutrient_vector, ingredients=ingredient_terms, params=params)
            recommendations = model.output_recommended_recipes(raw_results) or []
            if not recommendations:
                info_message = "No se encontraron recetas compatibles con esos valores. Prueba ampliando los rangos o quitando filtros." 
        except Exception as exc:  # pylint: disable=broad-except
            error = str(exc)

    return render_template(
        "custom.html",
        nutrient_fields=CUSTOM_NUTRIENT_FIELDS,
        defaults=defaults,
        recommendations=recommendations,
        error=error,
        info_message=info_message,
        ingredients_input=ingredients_input,
        recommendation_count=recommendation_count,
    )


if __name__ == "__main__":
    app.run(debug=True)
