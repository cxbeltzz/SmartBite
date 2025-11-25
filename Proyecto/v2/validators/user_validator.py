"""
Esta clase ayuda a validar datos del formulario de creación de cuenta
"""
class UserValidator:
    @staticmethod
    def validate(user):
        UserValidator.check_username(user.username)
        UserValidator.check_password(user.password)
        UserValidator.check_fullname(user.fullname)

    @staticmethod
    def check_username(username):
        if len(username) < 3:
            raise ValueError("Nombre de usuario muy corto")
    
    @staticmethod
    def check_password(password):
        if len(password) < 8: # Por ahora voy a validar solo la longitud de la contraseña, pero toca poner más validaciones, como caracteres especiales y asi
            raise ValueError("Contraseña muy corta. Debe tener mínimo 8 caracteres")

    @staticmethod
    def check_fullname(fullname):
        _fullname = fullname.split(" ")
        if len(_fullname) < 3:
            raise ValueError("Debe poner su nombre completo")
        if len(fullname) >= 200:
            raise ValueError("Nombre muy largo")
        if len(fullname) < 10:
            raise ValueError("Nombre muy corto")