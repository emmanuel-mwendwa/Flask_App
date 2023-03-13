from datetime import datetime
from flask import render_template, session, redirect, url_for, current_app
from flask_login import login_required, current_user
from . import main
from .forms import NameForm, EditProfileForm
from .. import db
from ..models import User
from app.email import send_email

@main.route('/')
def index():
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
            if current_app.config['FLASKY_ADMIN']:
                send_email(current_app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
        else:
            session["known"] = True
        session["name"] = form.name.data
        form.name.data = ''
        return redirect(url_for(".index"))
    return render_template("index.html", current_time=datetime.utcnow(), form=form, name=session.get("name"), known=session.get("known", False))
    

@main.route('/user/<username>', methods=["POST", "GET"])
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template("user.html", user=user)

@main.route('/edit-profile', methods=["POST", "GET"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        return redirect(url_for('main.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)
