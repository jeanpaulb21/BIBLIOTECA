from flask import Flask
from app.extensions import db, login_manager, mail
from app.models import Usuario
from app.routes import main
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(rol='administrador').first():
            admin = Usuario(username='admin', correo='admin@biblioteca.com', rol='administrador')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Usuario administrador creado: usuario=admin, contraseña=admin123")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
