from .entities.User import User
from werkzeug.security import generate_password_hash
from config import dsn
import psycopg2
from psycopg2.extensions import connection as PGConnection
from flask_login import current_user
import traceback
import secrets
from datetime import datetime, timedelta, timezone

class ModelUser:

    @classmethod
    def login(cls, user):
        """
        Busca el usuario por email, verifica la contraseña y devuelve un objeto User.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, email, full_name FROM user_account WHERE email = %s",
                        (user.username,)
                    )
                    row1 = cursor.fetchone()
                    if not row1:
                        return None

                    user_id, email, full_name = row1

                    cursor.execute(
                        "SELECT password_hash FROM auth_credential WHERE user_id = %s",
                        (user_id,)
                    )
                    row2 = cursor.fetchone()
                    stored_hash = row2[0] if row2 else None

                    cursor.execute(
                        "UPDATE auth_credential SET last_login_at = now() WHERE user_id = %s",
                        (user_id,)
                    )

                    password_ok = False
                    try:
                        if stored_hash is not None:
                            password_ok = User.check_password(stored_hash, user.password)
                    except Exception:
                        traceback.print_exc()
                        password_ok = False

                    _user = User(user_id, email, password_ok, full_name)

                    if password_ok:
                        cursor.execute(
                            "UPDATE user_account SET is_active = true WHERE email = %s",
                            (email,)
                        )
                    return _user
        except Exception as ex:
            print("Excepción en ModelUser.login:", ex)
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_by_id(cls, id):
        """
        Busca el usuario por id y lo retorna.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, email, full_name, profile_pic FROM user_account WHERE id = %s",
                        (id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None
                    user_id, email, full_name, profile_pic = row
                    user = User(user_id, email, None, full_name)
                    user.profile_pic = profile_pic  # ← Agrega esto
                    return user
        except Exception as ex:
            print("Excepción en ModelUser.get_by_id:", ex)
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def logout(cls):
        """
        Actualiza is_active = false para el usuario actual (current_user).
        No lanza excepción al usuario; registra trazas si algo falla.
        """
        conn: PGConnection = None
        try:
            if not current_user or not getattr(current_user, "username", None):
                return
            email = current_user.username
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_account SET is_active = false WHERE email = %s",
                        (email,)
                    )
        except Exception as ex:
            print("Excepción en ModelUser.logout:", ex)
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    @classmethod
    def create_account(cls, user):
        """
        Crea una cuenta local (email, full_name) y la credencial con hash de contraseña.
        Usa RETURNING id para evitar consultas adicionales.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO user_account (email, full_name) VALUES (%s, UPPER(%s)) RETURNING id",
                        (user.username, user.fullname)
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise Exception("No se pudo insertar user_account")
                    user_id = row[0]

                    password_hash = generate_password_hash(user.password)
                    cursor.execute(
                        "INSERT INTO auth_credential (user_id, password_hash) VALUES (%s, %s)",
                        (user_id, password_hash)
                    )
                    return user_id
        except Exception as ex:
            print("Excepción en ModelUser.create_account:", ex)
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()

    @classmethod
    def user_exits(cls, email):
        """
        Retorna user_id si existe, sino None.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM user_account WHERE email = %s",
                        (email,)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as ex:
            print("Excepción en ModelUser.user_exits:", ex)
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_by_google_id(cls, google_id):
        """
        Busca el usuario por el google_id y luego lo retrna
        """
        conn = None
        try:
            conn = psycopg2.connect(dsn)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, email, full_name, google_id, profile_pic, oauth_provider "
                    "FROM user_account WHERE google_id = %s",
                    (google_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    print("El usuario no había iniciado sesión por Google (no encontrado).")
                    return None

                user_id, email, full_name, google_id_db, profile_pic, oauth_provider = row

                cursor.execute(
                    "SELECT password_hash FROM auth_credential WHERE user_id = %s",
                    (user_id,)
                )
                row2 = cursor.fetchone()
                password_hash = row2[0] if row2 else None

                user = User(user_id, email, password_hash, full_name)

                user.google_id = google_id_db
                user.profile_pic = profile_pic
                user.oauth_provider = oauth_provider

                return user

        except Exception as ex:
            print("Excepción en get_by_google_id:", ex)
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()

    @classmethod
    def create_google_user(cls, google_id, email, fullname, picture):
        """
        Inserta un usuario con oauth provider = 'google' y retorna el objeto User usando get_by_google_id.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO user_account (email, full_name, google_id, profile_pic, oauth_provider) "
                        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (email, fullname, google_id, picture, "google")
                    )
                    row = cursor.fetchone()
                    if not row:
                        raise Exception("No se pudo insertar user_account (google)")
                    password_hash = generate_password_hash("12345678")
                    cursor.execute(
                        "INSERT INTO auth_credential (user_id, password_hash) VALUES (%s, %s)",
                        (row[0], password_hash)
                    )
                    return cls.get_by_google_id(google_id)
        except Exception as ex:
            print("Excepción en ModelUser.create_google_user:", ex)
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()

    @classmethod
    def link_google_account(cls, user_id, google_id, picture):
        """
        Vincula una cuenta existente con google_id y actualiza profile_pic y oauth_provider.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_account SET google_id = %s, profile_pic = %s, oauth_provider = %s WHERE id = %s",
                        (google_id, picture, "google", user_id)
                    )
        except Exception as ex:
            print("Excepción en ModelUser.link_google_account:", ex)
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_by_email(cls, email):
        """
        Obtiene usuario por email (incluyendo password_hash si existe) y regresa un objeto User.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, email, full_name, google_id, profile_pic, oauth_provider FROM user_account WHERE email = %s",
                        (email,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None

                    user_id, user_email, full_name, google_id_db, profile_pic, oauth_provider = row

                    cursor.execute(
                        "SELECT password_hash FROM auth_credential WHERE user_id = %s",
                        (user_id,)
                    )
                    row2 = cursor.fetchone()
                    password_hash = row2[0] if row2 else None

                    user = User(user_id, user_email, password_hash, full_name)
                    user.google_id = google_id_db if len(row) > 4 else None
                    user.profile_pic = profile_pic if len(row) > 5 else None
                    user.oauth_provider = oauth_provider if len(row) > 6 else None

                    return user
        except Exception as ex:
            print("Excepción en ModelUser.get_by_email:", ex)
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def create_password_reset_token(cls, email):
        """
        Crea un token de recuperación de contraseña para un email.
        Retorna el token si el usuario existe, None si no existe.
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM user_account WHERE email = %s",
                        (email,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    user_id = row[0]
                    
                    token = secrets.token_urlsafe(32)
                    expires_at = datetime.now() + timedelta(hours=1)  
                    
                    cursor.execute(
                        """
                        INSERT INTO password_reset_token (user_id, token, expires_at)
                        VALUES (%s, %s, %s)
                        RETURNING token
                        """,
                        (user_id, token, expires_at)
                    )
                    
                    return token
        except Exception as ex:
            print("Excepción en create_password_reset_token:", ex)
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def validate_reset_token(cls, token):
        """
        Valida un token de recuperación.
        Retorna user_id si es valido y None si no lo es
        """
        conn: PGConnection = None
        try:
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT user_id, expires_at, used
                        FROM password_reset_token
                        WHERE token = %s
                        """,
                        (token,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    user_id, expires_at, used = row
                    
                    # Verificar que no haya sido usado
                    if used:
                        return None
                    
                    # Verificar que no haya expirado
                    if datetime.now(timezone.utc) > expires_at:
                        return None
                    
                    return user_id
        except Exception as ex:
            print("Excepción en validate_reset_token:", ex)
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def reset_password(cls, token, new_password):
        """
        Resetea la contraseña de un usuario usando un token válido.
        Retorna True si fue exitoso y False si no
        """
        conn: PGConnection = None
        try:
            user_id = cls.validate_reset_token(token)
            if not user_id:
                return False
            
            conn = psycopg2.connect(dsn)
            with conn:
                with conn.cursor() as cursor:
                    # Actualizar la contraseña
                    from werkzeug.security import generate_password_hash
                    password_hash = generate_password_hash(new_password)
                    
                    cursor.execute(
                        """
                        UPDATE auth_credential
                        SET password_hash = %s
                        WHERE user_id = %s
                        """,
                        (password_hash, user_id)
                    )
                    
                    # Marcar el token como usado
                    cursor.execute(
                        """
                        UPDATE password_reset_token
                        SET used = true
                        WHERE token = %s
                        """,
                        (token,)
                    )
                    
                    return True
        except Exception as ex:
            print("Excepción en reset_password:", ex)
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()
