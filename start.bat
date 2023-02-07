CALL env\Scripts\activate.bat

set FLASK_APP=main.py
set FLASK_DEBUG=1
set SECRET_KEY=this is my secret key
set MAIL_PORT=587
set MAIL_USERNAME=unit.test.26@gmail.com
set MAIL_PASSWORD=zrccjewjsmcdxipx
set FLASKY_ADMIN=unit.test.26@gmail.com

flask run
