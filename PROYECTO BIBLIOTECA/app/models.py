from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Enum

db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relaciones
    prestamos = db.relationship("Prestamo", back_populates="usuario", cascade="all, delete-orphan")
    reservas = db.relationship("Reserva", back_populates="usuario", cascade="all, delete-orphan")
    favoritos = db.relationship("Favorito", back_populates="usuario", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}')>"

class Libro(db.Model):
    __tablename__ = 'libros'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(100))
    cantidad_total = db.Column(db.Integer, default=0, nullable=False)
    cantidad_disponible = db.Column(db.Integer, default=0, nullable=False)
    fecha_publicacion = db.Column(db.Date)
    editorial = db.Column(db.String(100))
    isbn_base = db.Column(db.String(20), unique=True, nullable=False)  # Cambiado de isbn a isbn_base
    descripcion = db.Column(db.Text)
    disponible = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relaciones
    prestamos = db.relationship("Prestamo", back_populates="libro", cascade="all, delete-orphan")
    reservas = db.relationship("Reserva", back_populates="libro", cascade="all, delete-orphan")
    favoritos = db.relationship("Favorito", back_populates="libro", cascade="all, delete-orphan")
    ejemplares = db.relationship("Ejemplar", back_populates="libro", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Libro(id={self.id}, titulo='{self.titulo}')>"

class Ejemplar(db.Model):
    __tablename__ = 'ejemplares'

    id = db.Column(db.Integer, primary_key=True)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    estado = db.Column(Enum('disponible', 'prestado', 'reservado', name='estado_ejemplar'), default='disponible')

    libro = db.relationship("Libro", back_populates="ejemplares")

    def __repr__(self):
        return f"<Ejemplar(id={self.id}, isbn={self.isbn}, estado={self.estado})>"

    @staticmethod
    def generar_isbn_unico(libro):
        total_ejemplares = Ejemplar.query.filter_by(libro_id=libro.id).count()
        nuevo_isbn = f"{libro.isbn_base}{str(total_ejemplares).zfill(3)}"  # Ejemplo: 9870000 + 000, 001, 002...
        return nuevo_isbn

class Prestamo(db.Model):
    __tablename__ = 'prestamos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_prestamo = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    fecha_devolucion_esperada = db.Column(db.Date, nullable=False)
    fecha_devolucion_real = db.Column(db.Date)
    estado = db.Column(Enum('prestado', 'devuelto', 'atrasado', name='estado_prestamo'), nullable=False, default='prestado')

    # Relaciones
    libro = db.relationship("Libro", back_populates="prestamos")
    usuario = db.relationship("Usuario", back_populates="prestamos")

    def __repr__(self):
        return f"<Prestamo(id={self.id}, libro_id={self.libro_id}, usuario_id={self.usuario_id})>"

class Reserva(db.Model):
    __tablename__ = 'reservas'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_reserva = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_expiracion = db.Column(db.Date)
    estado = db.Column(Enum('activa', 'completada', 'cancelada', name='estado_reserva'), nullable=False, default='activa')

    # Relaciones
    libro = db.relationship("Libro", back_populates="reservas")
    usuario = db.relationship("Usuario", back_populates="reservas")

    def __repr__(self):
        return f"<Reserva(id={self.id}, libro_id={self.libro_id}, usuario_id={self.usuario_id})>"

class Favorito(db.Model):
    __tablename__ = 'favoritos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    fecha_agregado = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    usuario = db.relationship("Usuario", back_populates="favoritos")
    libro = db.relationship("Libro", back_populates="favoritos")

    def __repr__(self):
        return f"<Favorito(id={self.id}, usuario_id={self.usuario_id}, libro_id={self.libro_id})>"
