from .entities.User import User

from werkzeug.security import generate_password_hash

from config import dsn

import psycopg2
from psycopg2.extensions import connection as PGConnection
from flask_login import current_user


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
