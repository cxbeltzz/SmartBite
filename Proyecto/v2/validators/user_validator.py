from flask import flash

"""
Esta clase ayuda a validar datos del formulario de creación de cuenta
"""
class UserValidator:
    @staticmethod
    def validate_register(user):
        UserValidator.check_username(user.username)
        UserValidator.check_password(user.password)
        UserValidator.check_fullname(user.fullname)
    
    @staticmethod
    def check_username_log(email):
        """
        Método para verificar si el correo dado es válido (tiene el @unal.edu.co)
        Param: email
        Return: True si el email es válido
        """
        return email.split("@")[1] == "unal.edu.co"

    @staticmethod
    def username_log(email):
        """
        Método para obtener el user de un correo dado
        Param: email
        Return: usuario de correo sin el "@unal.edu.co"
        """
        username = email.split("@")
        return username[0]

    @staticmethod
    def check_username(username):
        """
        Mira si un nombre de usuario cumple con una longitud mínima de 3 caracteres
        """
        if len(username) < 3:
            raise ValueError("Nombre de usuario muy corto")
    
    @staticmethod
    def check_password(password):
        """
        Mira si la contraseña dada cumple con ciertos parámetros para ser válida
        """
        if len(password) < 8: # Por ahora voy a validar solo la longitud de la contraseña, pero toca poner más validaciones, como caracteres especiales y asi
            raise ValueError("Contraseña muy corta. Debe tener mínimo 8 caracteres")
    
    @staticmethod
    def check_password_equals(password, confirm_password):
        """
        Método que confirma si las dos contraseñas dadas en el registro son iguales
        """
        if password != confirm_password:
            return  False
        return True

    @staticmethod
    def check_fullname(fullname):
        "Mira si el nombre completo dado es válido"
        _fullname = fullname.split(" ")
        if len(_fullname) < 3:
            raise ValueError("Debe poner su nombre completo")
        if len(fullname) >= 200:
            raise ValueError("Nombre muy largo")
        if len(fullname) < 10:
            raise ValueError("Nombre muy corto")