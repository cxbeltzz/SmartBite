import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import secrets
from datetime import datetime
import model
import config
import traceback
from dotenv import load_dotenv
load_dotenv()

from urllib.parse import quote # Por una cuestión de un "%" en mi base de datos local

# Modelos
from models.ModelUser import ModelUser
from models.ModelSavedRecipe import ModelSavedRecipe

# Entidades
from models.entities.User import User

# Utilidades
from validators.user_validator import UserValidator
from utils.decorators import logout_required

# Para manejar las sesiones
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage

#POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:password@db:5432/v2")
# POSTGRES_DSN = "postgresql://postgres:password@db:5432/v2"
POSTGRES_DSN = "postgresql://postgres:" + quote("postsoft%22") + "@localhost:5433/modelo" # Pruebas fuera del contenedor

app = Flask(__name__)

# Para la base de datos de los usuarios
app.config['SQLALCHEMY_DATABASE_URI'] = config.dsn
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Para los emails
app.config.from_object(config.Config)
mail = Mail(app)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app.secret_key = config.Config.SECRET_KEY

db = SQLAlchemy(app)
login_manager_app = LoginManager(app)

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


@app.route("/home", methods=["GET", "POST"])
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
    
    # Variable para saber si mostrar opciones de guardado
    show_save_options = current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
    
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
            
            _get_dataframe()
            bmi, bmi_status = calculate_bmi(user.weight_kg, user.height_cm)
            tdee = calculate_tdee(user)
            targets = plan_targets(tdee)
            selected_plan = targets[user.plan]
            calories_per_meal = selected_plan["calories"] / max(user.meals_per_day, 1)
            recommendations = recommend_meals(calories_per_meal, user.meals_per_day)
            
            # Construir meal_labels y flat_recommendations
            flat_recommendations = []
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
            
            # CONSTRUIR RESULT UNA SOLA VEZ CON TODA LA INFORMACIÓN
            result = {
                "bmi": bmi,
                "bmi_status": bmi_status,
                "tdee": round(tdee),
                "targets": targets,
                "selected_plan_key": user.plan,
                "selected_plan": selected_plan,
                "meals_per_day": user.meals_per_day,
                "recommendations": recommendations,
                "user": {  # ← user como diccionario, NO como objeto UserInput
                    "age": user.age,
                    "height_cm": user.height_cm,
                    "weight_kg": user.weight_kg,
                    "gender": user.gender,
                    "activity": user.activity,
                    "plan": user.plan,
                    "meals_per_day": user.meals_per_day
                },
                "macro_total": compute_macro_targets(selected_plan["calories"]),
                "macro_per_meal": compute_macro_targets(calories_per_meal),
                "meal_labels": meal_labels,
                "flat_recommendations": flat_recommendations,
                "meal_order": meal_order
            }
            
            composition_payload = {
                "active": True,
                "meal_labels": meal_labels,
                "recommendations": recommendations,
                "meal_order": meal_order,
                "plan_calories": selected_plan["calories"],
                "macro_targets_day": result["macro_total"],
                "macro_targets_meal": result["macro_per_meal"],
            }
                    
        except Exception as exc:
            error = str(exc)
            import traceback
            traceback.print_exc()
    
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
        show_save_options=show_save_options
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

@login_manager_app.user_loader
def load_user(id):
    return ModelUser.get_by_id(id)

@app.route("/login", methods=["GET", "POST"])
@logout_required
def login():
    if request.method == "POST":
        email = request.form.get("email").replace(" ", "")
        password = request.form.get("password")
        remember = request.form.get("remember")
        
        if UserValidator.check_username_log(email):
            user = User(0, UserValidator.username_log(email), password)
            logged_user = ModelUser.login(user)
            
            if logged_user != None:
                if logged_user.password:
                    login_user(logged_user)
                    return redirect(url_for('index'))
                else:
                    flash("Contraseña Inválida", "error")
            else:
                flash("Usuario Inválido", "error")
        else:
            flash("Correo Inválido", "error")
    return render_template("auth/login.html")

@app.route("/logout")
def logout():
    ModelUser.logout()
    logout_user()
    session.pop('_flashes', None)
    return redirect(url_for('index'))

@app.route("/protected")
@login_required
def protected():
    return "<h1>Esta es una vista protegida, solo para usuarios autenticados.</h1>"

@app.route("/register", methods=["GET", "POST"])
@logout_required
def register():
    if request.method == "POST":
        fullname = request.form.get("name")
        email = request.form.get("email").replace(" ", "")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        terms = request.form.get("terms")
        
        # Validaciones
        if not all([fullname, email, password, confirm_password]):
            flash("Completa todos los campos", "error")
            return redirect(url_for('register'))
        if UserValidator.check_username_log(email):
            registration = User(None, UserValidator.username_log(email), password, fullname)
            try:
                UserValidator.validate_register(registration)
                if UserValidator.check_password_equals(password, confirm_password):
                    if not terms:
                        flash("Debes aceptar los términos y condiciones", "error")
                        return redirect(url_for('register'))
                    else:
                        ModelUser.create_account(registration)
                        return redirect(url_for('login'))
                else:
                    flash("Las contraseñas no coinciden", "error")
                    return redirect(url_for('register'))
            except Exception as VE:
                flash(str(VE))
                return redirect(url_for('register'))
        else:
            flash("Solo usuarios de la UNAL", "error")
            return redirect(url_for('register'))
    return render_template("auth/register.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        if not email:
            flash("Ingresa tu correo electrónico")
            return redirect(url_for('forgot_password'))
        
        if not UserValidator.check_username_log(email):
            flash("Correo inválido")
            return redirect(url_for('forgot_password'))
        normalized_email = UserValidator.username_log(email)

        token = ModelUser.create_password_reset_token(normalized_email)
        
        if token:
            reset_url = url_for('reset_password', token=token, _external=True)
            
            try:
                msg = Message(
                    subject="Recuperación de contraseña - SmartBite",
                    recipients=[normalized_email + "@unal.edu.co"],
                    html=f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; background-color: #080b2c; color: #e2e8f0; padding: 20px;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #101534; border-radius: 12px; padding: 30px; border: 1px solid rgba(255,255,255,0.1);">
                            <h1 style="color: #a855f7; margin-bottom: 20px;">Recuperación de Contraseña</h1>
                            <p style="margin-bottom: 20px;">Hola,</p>
                            <p style="margin-bottom: 20px;">Recibimos una solicitud para restablecer la contraseña de tu cuenta en SmartBite.</p>
                            <p style="margin-bottom: 30px;">Haz clic en el botón de abajo para crear una nueva contraseña. Este enlace expirará en 1 hora.</p>
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{reset_url}" style="background-color: #a855f7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold;">
                                    Restablecer Contraseña
                                </a>
                            </div>
                            <p style="margin-top: 30px; font-size: 14px; color: #94a3b8;">Si no solicitaste este cambio, puedes ignorar este email de forma segura.</p>
                            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
                            <p style="font-size: 12px; color: #64748b; text-align: center;">SmartBite - Recomendaciones Nutricionales</p>
                        </div>
                    </body>
                    </html>
                    """
                )
                mail.send(msg)
                flash("Se ha enviado un enlace de recuperación a tu correo electrónico")
            except Exception as e:
                print(f"Error enviando email: {e}")
                traceback.print_exc()
                flash("Error al enviar el email. Por favor intenta más tarde.")
        else:
            # Voy a hacer que se muestre el mismo mensaje aunque el usuario no exista :)
            flash("Si existe una cuenta con ese correo, recibirás un enlace de recuperación")
        
        return redirect(url_for('login'))
    
    return render_template("auth/forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user_id = ModelUser.validate_reset_token(token)
    
    if not user_id:
        flash("El enlace de recuperación es inválido o ha expirado")
        return redirect(url_for('forgot_password'))
    
    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not new_password or not confirm_password:
            flash("Por favor completa todos los campos")
            return render_template("auth/reset_password.html", token=token)
        
        if not UserValidator.check_password_equals(new_password, confirm_password):
            flash("Las contraseñas no coinciden")
            return render_template("auth/reset_password.html", token=token)
        try:
            UserValidator.check_password(new_password)
        except Exception as e:
            flash(str(e))
            return render_template("auth/reset_password.html", token=token)
        
        # Resetear la contraseña
        if ModelUser.reset_password(token, new_password):
            flash("Tu contraseña ha sido actualizada exitosamente")
            return redirect('/login')
        else:
            flash("Error al actualizar la contraseña. Por favor intenta de nuevo.")
            return render_template("auth/reset_password.html", token=token)
    
    return render_template("auth/reset_password.html", token=token)

google_bp = make_google_blueprint(
    client_id = config.Config.GOOGLE_OAUTH_CLIENT_ID,
    client_secret = config.Config.GOOGLE_OAUTH_CLIENT_SECRET,
    scope = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    redirect_to = "index"
)

app.register_blueprint(google_bp, url_prefix = "/login")

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    """Obtiene el nombre completo y el email por medio de Google OAuth para iniciar sesión"""

    if not token:
        flash("Error: token no recibido de Google.", "error")
        return False

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Error al obtener información de Google.", "error")
        return False

    info = resp.json()
    google_id = info.get("id")
    email = info.get("email")
    name = info.get("name", "")
    picture = info.get("picture", "")

    if not google_id or not email:
        flash("Respuesta incompleta de Google.", "error")
        return False

    try:
        user = ModelUser.get_by_google_id(google_id)
        if not user:
            user = ModelUser.get_by_email(UserValidator.username_log(email))
            if user:
                ModelUser.link_google_account(user.id, google_id, picture)
            else:
                user = ModelUser.create_google_user(
                    google_id = google_id,
                    email = UserValidator.username_log(email),
                    fullname = name,
                    picture = picture
                )

        login_user(user)
        flash(f"Bienvenido {user.fullname}!", "success")
    except Exception as exc:
        flash("Error interno al autenticar con Google.", "error")
    return False

@app.route("/dashboard")
@login_required
def dashboard():
    """Vista principal del dashboard para usuarios autenticados"""
    try:
        user_id = current_user.id
        
        # Obtener recetas guardadas
        saved_recipes = ModelSavedRecipe.get_user_saved_recipes(user_id)
        favorites_count = sum(1 for recipe in saved_recipes if recipe['is_favorite'])
        
        # Obtener planes nutricionales
        meal_plans = ModelSavedRecipe.get_user_meal_plans(user_id)
        active_plan = ModelSavedRecipe.get_active_meal_plan(user_id)
        
        return render_template(
            "dashboard.html",
            saved_recipes=saved_recipes,
            favorites_count=favorites_count,
            meal_plans=meal_plans,
            active_plan=active_plan
        )
    except Exception as ex:
        flash("Error al cargar el dashboard", "error")
        return redirect("/")

@app.route("/dashboard/save-recipe", methods=["POST"])
@login_required
def save_recipe():
    """Guarda una receta en el perfil del usuario"""
    try:
        data = request.get_json(force=True, silent=True)
        print("DEBUG - Datos recibidos:", type(data), str(data)[:200])

        if data is None:
            return jsonify({"success": False, "message": "JSON no recibido"}), 400

        # para aceptar ambos formatos
        if "recipe_data" in data:
            recipe_data = data["recipe_data"]
            notes = data.get("notes", "")
        else:
            recipe_data = data
            notes = ""

        if not isinstance(recipe_data, dict):
            return jsonify({"success": False, "message": "recipe_data debe ser un objeto"}), 400

        saved_id = ModelSavedRecipe.save_recipe(
            user_id=current_user.id,
            recipe_data=recipe_data,
            notes=notes
        )

        return jsonify({
            "success": True,
            "saved_id": saved_id,
            "message": "Receta guardada exitosamente"
        }), 200

    except Exception as ex:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": str(ex)
        }), 500 


@app.route("/dashboard/toggle-favorite/<int:saved_recipe_id>", methods=["POST"])
@login_required
def toggle_favorite(saved_recipe_id):
    """Marca o desmarca una receta como favorita"""
    try:
        is_favorite = ModelSavedRecipe.toggle_favorite(current_user.id, saved_recipe_id)
        
        if is_favorite is None:
            return jsonify({
                "success": False,
                "message": "Receta no encontrada"
            }), 404
        
        return jsonify({
            "success": True,
            "is_favorite": is_favorite
        }), 200
    except Exception as ex:
        print(f"Error al marcar favorito: {ex}")
        return jsonify({
            "success": False,
            "message": str(ex)
        }), 500


@app.route("/dashboard/delete-recipe/<int:saved_recipe_id>", methods=["POST"])
@login_required
def delete_saved_recipe(saved_recipe_id):
    """Elimina una receta guardada"""
    try:
        success = ModelSavedRecipe.delete_saved_recipe(current_user.id, saved_recipe_id)
        
        if not success:
            return jsonify({
                "success": False,
                "message": "Receta no encontrada"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Receta eliminada exitosamente"
        }), 200
    except Exception as ex:
        print(f"Error al eliminar receta: {ex}")
        return jsonify({
            "success": False,
            "message": str(ex)
        }), 500


@app.route("/dashboard/save-plan", methods=["POST"])
@login_required
def save_meal_plan():
    """Guarda un plan nutricional completo"""
    try:
        data = request.get_json()
        plan_data = data.get('plan_data')
        user_profile = data.get('user_profile')
        plan_name = data.get('plan_name', f"Plan {datetime.now().strftime('%d/%m/%Y')}")
        
        plan_id = ModelSavedRecipe.save_meal_plan(
            user_id=current_user.id,
            plan_data=plan_data,
            user_profile=user_profile,
            plan_name=plan_name
        )
        
        return jsonify({
            "success": True,
            "plan_id": plan_id,
            "message": "Plan guardado exitosamente"
        }), 200
    except Exception as ex:
        print(f"Error al guardar plan: {ex}")
        return jsonify({
            "success": False,
            "message": str(ex)
        }), 500


@app.route("/dashboard/plan/<int:plan_id>")
@login_required
def view_meal_plan(plan_id):
    """Vista detallada de un plan nutricional"""
    try:
        plans = ModelSavedRecipe.get_user_meal_plans(current_user.id)
        plan = next((p for p in plans if p['id'] == plan_id), None)
        
        if not plan:
            flash("Plan no encontrado")
            return redirect(url_for('dashboard'))
        
        # Reconstruir el resultado para usar el template de index
        result = plan['plan_data']
        result['user'] = plan['user_profile']
        
        return render_template(
            "meal_plan_view.html",
            plan=plan,
            result=result,
            activities=ACTIVITY_LEVELS,
            plans=WEIGHT_PLANS
        )
    except Exception as ex:
        print(f"Error al ver plan: {ex}")
        flash("Error al cargar el plan")
        return redirect(url_for('dashboard'))

@app.route("/dashboard/activate-plan/<int:plan_id>", methods=["POST"])
@login_required
def activate_meal_plan(plan_id):
    """Activa un plan nutricional existente"""
    try:
        success = ModelSavedRecipe.activate_meal_plan(current_user.id, plan_id)

        if not success:
            message = "Plan no encontrado o no autorizado"
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": False, "message": message}), 404
            flash(message)
            return redirect(url_for("dashboard"))

        message = "Plan activado exitosamente"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "message": message})
        flash(message)
        return redirect(url_for("dashboard"))

    except Exception as ex:
        # Debug
        traceback.print_exc()
        message = "Error al activar el plan"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": str(ex)}), 500
        flash(message)
        return redirect(url_for("dashboard"))


# Hacer de esta la vista principal
@app.route("/")
def main():
    return render_template("main.html")


def status_401(error):
    return redirect(url_for('login'))

# Queda pendiente hacer una vista más elegante para cuando pase esto
def status_404(error):
    return "<h1>Página no encontrada</h1>", 404

if __name__ == "__main__":
    app.config.from_object(config.DevelopmentConfig)
    app.register_error_handler(401, status_401)
    app.register_error_handler(404, status_404)

    app.run(debug=True)
