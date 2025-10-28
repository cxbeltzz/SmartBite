import os
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


def recommend_meals(calories_per_meal: float) -> Dict[str, List[dict]]:
    vector = build_nutrient_vector(calories_per_meal)
    dataframe = _get_dataframe()
    params = {"n_neighbors": 15, "return_distance": False}
    recommendations = model.recommend(dataframe, vector, params=params)
    if recommendations is None:
        return {"breakfast": [], "lunch": [], "dinner": []}
    records = model.output_recommended_recipes(recommendations)
    # Garantiza que cada comida reciba recetas distintas.
    unique_records = records[:15]
    breakfast = unique_records[0:5]
    lunch = unique_records[5:10]
    dinner = unique_records[10:15]
    return {
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
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
            recommendations = recommend_meals(calories_per_meal)
            result = {
                "bmi": bmi,
                "bmi_status": bmi_status,
                "tdee": round(tdee),
                "targets": targets,
                "selected_plan_key": user.plan,
                "meals_per_day": user.meals_per_day,
                "recommendations": recommendations,
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
    )


if __name__ == "__main__":
    app.run(debug=True)
