def username(email):
    """
    Funcion para obtener el user de un correo dado
    Param: email
    Return: usuario de correo sin el "@unal.edu.co"
    """
    username = email.split("@")
    return username[0]
