def username(email):
    """
    Funcion para obtener el user de un correo dado
    Param: email
    Return: usuario de correo sin el "@unal.edu.co"
    """
    _ = email.split("@")
    return _[0]
