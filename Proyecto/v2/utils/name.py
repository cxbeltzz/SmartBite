def name(fullname:str):
    """
    Función para extraer el primer nombre y el primer apellido de un usuario. \n
    Param: fullname \n
    Return: Primer Nombre + Primer apellido
    """

    names = fullname.split(" ")
    if len(names) == 4:
        return names[0].capitalize() + " " + names[2].capitalize()
    elif len(names) == 3:
        return names[0].capitalize() + " " + names[1].capitalize()