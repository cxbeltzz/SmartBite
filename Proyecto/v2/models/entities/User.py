from werkzeug.security import check_password_hash
from flask_login import UserMixin
from utils.name import name

class User(UserMixin):

    def __init__(self, id, username, password, fullname = "") -> None:
        self.id = id
        self.username = username # username del correo UNAL
        self.password = password
        self.fullname = fullname
        self.name = name(fullname) # Para usarlo en la navbar
        self.google_id = None
        self.profile_pic = None
        self.oauth_provider = None
    
    @classmethod
    def check_password(self, hashed_password, password):
        return check_password_hash(hashed_password, password)
    
    