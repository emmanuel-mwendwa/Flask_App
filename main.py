import os
from app import create_app, db
from app.models import User, Role
from flask_migrate import Migrate


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


# this function returns a dictionary that includes the database instance and the models
# the flask shell command will import these items automatically into the shell
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

