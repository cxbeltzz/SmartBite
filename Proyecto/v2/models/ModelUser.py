from .entities.User import User

from werkzeug.security import generate_password_hash

from config import dsn

import psycopg2
from psycopg2.extensions import connection as PGConnection
from flask_login import current_user
import traceback


class ModelUser():

    @classmethod
    def login(self, user):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    # Para obtener datos de user_account 
                    select_user =  "SELECT id, email, full_name FROM user_account WHERE email = '{}'".format(user.username)
                    cursor.execute(select_user)
                    row1 = cursor.fetchone()

                    if row1 != None:
                        #Consulta para la contraseña
                        select_user_passhash =  "SELECT password_hash FROM auth_credential WHERE user_id = '{}'".format(row1[0])
                        cursor.execute(select_user_passhash)
                        row2 = cursor.fetchone()

                        # Para actualizar la fecha de la última sesión de la cuenta
                        cursor.execute("UPDATE auth_credential set last_login_at = now() WHERE user_id = '{}'".format(row1[0]))

                        _user = User(row1[0], row1[1], User.check_password(row2[0], user.password), row1[2])
                        update_user = "UPDATE user_account set is_active = true WHERE email = '{}'".format(user.username)
                        cursor.execute(update_user)
                        return _user
                    else:
                        return None
        finally:
            connection.close()
    
    @classmethod
    def get_by_id(self, id):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    # Para obtener datos de user_account 
                    select_user =  "SELECT id, email, full_name FROM user_account WHERE id = '{}'".format(id)
                    cursor.execute(select_user)
                    row1 = cursor.fetchone()

                    if row1 != None:
                        return User(row1[0], row1[1], None, row1[2])
                    else:
                        return None
        finally:
            connection.close()
    
    @classmethod
    def logout(self):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    # Para cambiar el estado de la sesión en la base de datos
                    update_user =  "UPDATE user_account set is_active = false WHERE email = '{}'".format(current_user.username)
                    cursor.execute(update_user)
        finally:
            connection.close()

    @classmethod
    def create_account(self, user):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    insert_user = "INSERT INTO user_account (email, full_name) VALUES ('{}', UPPER('{}'))".format(user.username, user.fullname)
                    cursor.execute(insert_user)

                    # Para obtener el id
                    select_user_id = "SELECT id FROM user_account WHERE email = '{}'".format(user.username)
                    cursor.execute(select_user_id)
                    user_id = cursor.fetchone()[0]

                    insert_user_pass = "INSERT INTO auth_credential (user_id, password_hash) VALUES ('{}', '{}')".format(user_id, generate_password_hash(user.password))
                    cursor.execute(insert_user_pass)
        finally:
            connection.close()

    @classmethod
    def user_exits(self, email):
        """
        Método para mirar si un usuario existe
        :param self: Description
        :param email: Description
        :return: user_id si existe, sino None
        """
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    select_user_id = "SELECT id FROM user_account WHERE email = '{}'".format(email)
                    cursor.execute(select_user_id)
                    return cursor.fetchone()[0]
        finally:
            connection.close()
    
    @classmethod
    def get_by_google_id(cls, google_id):
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
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            cursor = connection.cursor()
            sql = "INSERT INTO user_account (email, full_name, google_id, profile_pic, oauth_provider) VALUES ('{}', '{}', '{}', '{}', 'google')".format(email, fullname, google_id, picture)
            cursor.execute(sql)
            # Obtener el usuario recien creado
            return cls.get_by_google_id(google_id)
        except Exception as ex:
            raise Exception(ex)
        finally:
            connection.close()
    
    @classmethod
    def link_google_account(cls, user_id, google_id, picture):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            cursor = connection.cursor()
            sql = "UPDATE user_account SET google_id = '{}', profile_pic = '{}', oauth_provider = 'google' WHERE id = '{}'".format(google_id, picture, user_id)
            cursor.execute(sql)
        except Exception as ex:
            raise Exception(ex)
        finally:
            connection.close()
    
    @classmethod
    def get_by_email(cls, email):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            cursor = connection.cursor()
            sql = "SELECT id, email, full_name, google_id, profile_pic, oauth_provider FROM user_account WHERE email = '{}'".format(email)
            cursor.execute(sql)
            row = cursor.fetchone()
            
            if row:
                #Consulta para la contraseña
                select_user_passhash =  "SELECT password_hash FROM auth_credential WHERE user_id = '{}'".format(row[0])
                cursor.execute(select_user_passhash)
                row2 = cursor.fetchone()

                user = User(row[0], row[1], row2[0], row[2])
                user.google_id = row[3] if len(row) > 4 else None
                user.profile_pic = row[4] if len(row) > 5 else None
                user.oauth_provider = row[5] if len(row) > 6 else None
                return user
            return None
        except Exception as ex:
            raise Exception(ex)
        finally:
            connection.close()
        