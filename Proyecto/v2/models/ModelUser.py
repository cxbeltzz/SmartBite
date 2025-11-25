from .entities.User import User

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
                    sql1 =  "SELECT id, email, full_name FROM user_account WHERE email = '{}'".format(user.username)
                    cursor.execute(sql1)
                    row1 = cursor.fetchone()

                    if row1 != None:
                        #Consulta para la contraseña
                        sql2 =  "SELECT password_hash FROM auth_credential WHERE user_id = '{}'".format(row1[0])
                        cursor.execute(sql2)
                        row2 = cursor.fetchone()

                        _user = User(row1[0], row1[1], User.check_password(row2[0], user.password), row1[2])
                        sql3 = "UPDATE user_account set is_active = true WHERE email = '{}'".format(user.username)
                        cursor.execute(sql3)
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
                    sql1 =  "SELECT id, email, full_name FROM user_account WHERE id = '{}'".format(id)
                    cursor.execute(sql1)
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
                    sql1 =  "UPDATE user_account set is_active = false WHERE email = '{}'".format(current_user.username)
                    cursor.execute(sql1)
        finally:
            connection.close()

    @classmethod
    def create_account(self, user):
        connection: PGConnection = psycopg2.connect(dsn)
