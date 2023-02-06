from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer

from . import db, login_manager

# database models in python code that will help in creating database tables with the defined columns and their attributes
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), unique=True)
    # a relationship btw User and Role
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(78), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    # a column formed from the relationship
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
     # password property
    password_hash = db.Column(db.String(128))
    # account confirmation
    confirmed = db.Column(db.Boolean, default=False)

    @property
    def password(self):
        raise AttributeError('what are you trying to do')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.confi['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def __repr__(self):
        return '<User %r>' % self.username


# function to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))