from functools import wraps
from flask import redirect, url_for
from flask_login import current_user

def logout_required(f):
    """
    Decorador que redirige a la página principal si el usuario ya está autenticado.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function