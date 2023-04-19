from flask import current_app, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from markdown import markdown
import bleach
import datetime
import jwt
import hashlib

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


# association table for the users
class Follow(db.Model):
    __tablename__ = "follows"

    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    

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
    # more details about the user
    # user names
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    # followed relationship
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    # followers relationship
    followers = db.relationship('Follow',
                               foreign_keys=[Follow.followed_id],
                               backref=db.backref('followed', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    # function to locate users last seen time
    def ping(self):
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    # setting the default role for users and an administrator
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
            if self.email is not None and self.avatar_hash is None:
                self.avatar_hash = self.gravatar_hash()
        
        self.follow(self)

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
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True
    
    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
    
    # use avatars from gravatar
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None
    
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()
    
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).\
                filter(Follow.follower_id == self.id)
    

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


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime(), index=True, default=datetime.datetime.utcnow())
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3']
        
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html', 
            tags=allowed_tags, strip=True)))


db.event.listen(Post.body, 'set', Post.on_changed_body)

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow())
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'strong', 'p']
        
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html', 
            tags=allowed_tags, strip=True)))
        
db.event.listen(Comment.body, 'set', Comment.on_changed_body)