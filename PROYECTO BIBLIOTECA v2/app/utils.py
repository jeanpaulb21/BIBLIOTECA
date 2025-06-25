from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generar_token(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='recuperar-contrasena')

def verificar_token(token, max_age=3600):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='recuperar-contrasena', max_age=max_age)
    except:
        return None
    return email
