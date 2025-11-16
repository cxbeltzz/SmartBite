from .entities.User import User

from config import dsn

import psycopg2
from psycopg2.extensions import connection as PGConnection

class ModelUser():

    @classmethod
    def login(self, db, user):
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
                        return _user
                    else:
                        return None
        finally:
            connection.close()
    
    @classmethod
    def get_by_id(self, db, user):
        connection: PGConnection = psycopg2.connect(dsn)
        try:
            with connection:
                with connection.cursor() as cursor:
                    # Para obtener datos de user_account 
                    sql1 =  "SELECT id, email, full_name FROM user_account WHERE email = '{}'".format(user.id)
                    cursor.execute(sql1)
                    row1 = cursor.fetchone()

                    if row1 != None:
                        return User(row1[0], row1[1], None, row1[2])
                    else:
                        return None
        finally:
            connection.close()
