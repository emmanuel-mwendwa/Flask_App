from flask import render_template
from flask_mail import Message
from threading import Thread
from . import mail, app

# adding a thread function to send email asynchronously
# this helps in making the page to not be unresponsive
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


# function that avoids having to create email messages manually every time
def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                    sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
