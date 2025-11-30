import json
import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor
from config import dsn
import traceback


class ModelSavedRecipe:
    
    @classmethod
    def save_recipe(cls, user_id, recipe_data, notes=None):
        """
        Guarda una receta para un usuario específico.
        """
        conn: PGConnection = None
        try:
            recipe_id = recipe_data.get('RecipeId') or recipe_data.get('RecipeID')
            recipe_name = recipe_data.get('Name')
            
            if not recipe_id or not recipe_name:
                raise ValueError("recipe_data debe contener RecipeId y Name")
            
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO user_saved_recipe 
                            (user_id, recipe_id, recipe_name, recipe_data, notes)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, recipe_id) 
                        DO UPDATE SET 
                            recipe_data = EXCLUDED.recipe_data,
                            notes = EXCLUDED.notes,
                            saved_at = now()
                        RETURNING id
                        """,
                        (user_id, recipe_id, recipe_name, json.dumps(recipe_data), notes)
                    )
                    return cursor.fetchone()[0]
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.save_recipe: {ex}")
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_user_saved_recipes(cls, user_id, favorites_only=False):
        """
        Obtiene todas las recetas guardadas de un usuario
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT 
                            id,
                            recipe_id,
                            recipe_name,
                            recipe_data,
                            is_favorite,
                            saved_at,
                            notes
                        FROM user_saved_recipe
                        WHERE user_id = %s
                    """
                    params = [user_id]
                    
                    if favorites_only:
                        query += " AND is_favorite = true"
                    
                    query += " ORDER BY saved_at DESC"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convertir JSONB a dict
                    recipes = []
                    for row in rows:
                        recipe = dict(row)
                        recipe['recipe_data'] = row['recipe_data']
                        recipes.append(recipe)
                    
                    return recipes
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.get_user_saved_recipes: {ex}")
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def delete_saved_recipe(cls, user_id, saved_recipe_id):
        """
        Elimina una receta guardada.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM user_saved_recipe
                        WHERE id = %s AND user_id = %s
                        """,
                        (saved_recipe_id, user_id)
                    )
                    return cursor.rowcount > 0
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.delete_saved_recipe: {ex}")
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def toggle_favorite(cls, user_id, saved_recipe_id):
        """
        Marca o desmarca una receta como favorita.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE user_saved_recipe
                        SET is_favorite = NOT is_favorite
                        WHERE id = %s AND user_id = %s
                        RETURNING is_favorite
                        """,
                        (saved_recipe_id, user_id)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.toggle_favorite: {ex}")
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def save_meal_plan(cls, user_id, plan_data, user_profile, plan_name=None):
        """
        Guarda un plan nutricional completo generado.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    # Desactivar planes anteriores
                    cursor.execute(
                        """
                        UPDATE user_meal_plan
                        SET is_active = false
                        WHERE user_id = %s AND is_active = true
                        """,
                        (user_id,)
                    )
                    
                    # Insertar nuevo plan
                    cursor.execute(
                        """
                        INSERT INTO user_meal_plan
                            (user_id, plan_name, plan_data, user_profile, is_active)
                        VALUES (%s, %s, %s, %s, true)
                        RETURNING id
                        """,
                        (user_id, plan_name, json.dumps(plan_data), json.dumps(user_profile))
                    )
                    return cursor.fetchone()[0]
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.save_meal_plan: {ex}")
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_user_meal_plans(cls, user_id):
        """
        Obtiene todos los planes nutricionales de un usuario
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id,
                            plan_name,
                            created_at,
                            plan_data,
                            user_profile,
                            is_active
                        FROM user_meal_plan
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user_id,)
                    )
                    rows = cursor.fetchall()
                    
                    plans = []
                    for row in rows:
                        plan = dict(row)
                        plan['plan_data'] = row['plan_data']
                        plan['user_profile'] = row['user_profile']
                        plans.append(plan)
                    
                    return plans
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.get_user_meal_plans: {ex}")
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_active_meal_plan(cls, user_id):
        """
        Obtiene el plan nutricional activo de un usuario
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            id,
                            plan_name,
                            created_at,
                            plan_data,
                            user_profile,
                            is_active
                        FROM user_meal_plan
                        WHERE user_id = %s AND is_active = true
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        plan = dict(row)
                        plan['plan_data'] = row['plan_data']
                        plan['user_profile'] = row['user_profile']
                        return plan
                    return None
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.get_active_meal_plan: {ex}")
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def activate_meal_plan(cls, user_id, plan_id):
        """
        Activa el plan con id=plan_id para el usuario user_id.
        Desactiva previamente cualquier otro plan activo del usuario.
        Devuelve True si el plan fue activado, False si no se encontró/actualizó.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    # Desactivar cualquier plan activo del usuario
                    cursor.execute(
                        """
                        UPDATE user_meal_plan
                        SET is_active = false
                        WHERE user_id = %s AND is_active = true
                        """,
                        (user_id,)
                    )

                    # Activar el plan solicitado (solo si pertenece al usuario)
                    cursor.execute(
                        """
                        UPDATE user_meal_plan
                        SET is_active = true
                        WHERE id = %s AND user_id = %s
                        """,
                        (plan_id, user_id)
                    )

                    # cursor.rowcount corresponde al número de filas actualizadas en la última query
                    return cursor.rowcount > 0
        except Exception as ex:
            print(f"Excepción en ModelSavedRecipe.activate_meal_plan: {ex}")
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()
