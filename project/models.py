from .database import getCredentials, getCredentialsbyId, queryAthlete, queryWorkoutData, queryTeam
from .database import addCredentialsJson
import bcrypt
from flask import session
from flask_login import UserMixin
from . import login_manager
from datetime import timedelta
from flask_jwt_extended import create_access_token, decode_token


class User(UserMixin):
    def __init__(self,  _id,  email, pwHash, salt):
        self._id = _id
        self.email = email
        self.pwHash = pwHash
        self.salt = salt

    def is_authenticated(self):
        return True
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        return str(self._id)

    def get_reset_token(self):
        return create_access_token(identity = self._id, expires_delta = timedelta(hours = 24))

    @staticmethod
    def verify_reset_token(token):
        try:
            userId = decode_token(token)['sub']
        except Exception as e:
            print(e)
            return
        return User.get_by_id(userId)

    @classmethod
    def get_by_email(cls, email):
        data = getCredentials(email)
        if data is not None:
            return cls(**data)

    @classmethod
    def get_by_id(cls, _id):
        data = getCredentialsbyId(_id)
        if data is not None:
            return cls(**data)

    @staticmethod
    def login_valid(email, password):
        verify_user = User.get_by_email(email)
        if verify_user is not None:
            return bcrypt.checkpw(password, verify_user.pwHash)
        return False

    @classmethod
    def register(cls, _id, email, pwHash, salt):
        user = cls.get_by_email(email)
        if user is None:
            new_user = cls(_id, email, pwHash, salt)
            new_user.save_to_mongo()
            session['email'] = email
            return True
        else:
            return False

    def json(self):
        return {
            "_id": self._id,
            "email": self.email,
            "pwHash": self.pwHash,
            "salt": self.salt,
        }

    def save_to_mongo(self):
        addCredentialsJson(self.json())


""" loads a user from the database, using their id as the key """
@login_manager.user_loader
def user_loader(user_id):
    user = User.get_by_id(int(user_id))
    if user is not None:
        return User(user._id, user.email, user.pwHash, user.salt)
    else:
        return None
