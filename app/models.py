from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
import datetime
import jwt

from . import db, login_manager

# database models in python code that will help in creating database tables with the defined columns and their attributes


# List of permissions in the application with constant values attached
class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), unique=True)
    #fields to assign roles and permissions to users
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    # a relationship btw User and Role
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role %r>' % self.name

    # methods to manage the permissions added
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    # setting default role
    def insert_roles():
        # listing the roles in the application
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
        }
        # declaring the default role
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


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

    # setting the default role for users and an administrator
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)
    
    def is_administrator(self):
        return self.can(Permission.ADMIN)

    @property
    def password(self):
        raise AttributeError('what are you trying to do')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        reset_token = jwt.encode({
            "confirm": self.id,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=expiration)
        },
        current_app.config['SECRET_KEY'],
        algorithm="HS256"
        )
        return reset_token

    def confirm(self, token):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=10),
                algorithms=["HS256"]
            )
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        reset_token = jwt.encode({
            "reset": self.id,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=expiration)
        },
        current_app.config['SECRET_KEY'],
        algorithm="HS256"
        )
        return reset_token

    @staticmethod
    def reset_password(token, new_password):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=10),
                algorithms=["HS256"]
            )
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True


    def generate_email_change_token(self, new_email, expiration=3600):
        reset_token = jwt.encode({
            "change_email": self.id,
            "new_email": new_email,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=expiration)
        },
        current_app.config['SECRET_KEY'],
        algorithm="HS256"
        )
        return reset_token

    def change_email(self, token):
        try:
            data = jwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    leeway=datetime.timedelta(seconds=10),
                    algorithms=["HS256"]
                )
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        return True

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False
    
    def is_administrator(self):
        return False
    
login_manager.anonymous_user = AnonymousUser

# function to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))