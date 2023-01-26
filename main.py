from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
import os

# absolute path for the database file
basedir = os.path.abspath(os.path.dirname(__file__))
#app initialization
app = Flask(__name__)
# helps in encryption and avoiding Cross Site Request Forgery(CSRF) attacks
app.config["SECRET_KEY"] = "hard to guess string"
# database connection string and name
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# mail sending configuration
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_MAIL_SENDER'] = 'Flasky admin <noreply@demo.com>'
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')

# Flask-Mail configuration for Gmail
app.config["MAIL_SERVER"] = "smtp.googlemail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get('MAIL_USERNAME')
app.config["MAIL_PASSWORD"] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)

# initializing migration script
migrate = Migrate(app, db)

# initializing flask-mail
mail = Mail(app)


# a FlaskForm model/class that helps create a HTML template form
class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


# database models in python code that will help in creating database tables with the defined columns and their attributes
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), unique=True)
    # a relationship btw User and Role
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    # a column formed from the relationship
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


# function that avoids having to create email messages manually every time
def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                    sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    mail.send(msg)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/user', methods=["POST", "GET"])
def user():
    form = NameForm()
    # validates the form using wtforms validators
    if form.validate_on_submit():
        # queries the database for a user by the name provided in the input field
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            # adds a new user to the database
            user = User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session["known"] = False
            # send email to app admin once any new names are added to the database
            if app.config['FLASKY_ADMIN']:
                send_email(app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
                print("Email sent")
        else:
            session["known"] = True
        session["name"] = form.name.data
        form.name.data = ''
        return redirect(url_for("user"))
    return render_template("user.html", form=form, name=session.get("name"), known=session.get("known", False))


# custom error handling pages
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# custom error handling pages
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


# this function returns a dictionary that includes the database instance and the models
# the flask shell command will import these items automatically into the shell
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


if __name__ == "__main__":
    app.run(debug=True)