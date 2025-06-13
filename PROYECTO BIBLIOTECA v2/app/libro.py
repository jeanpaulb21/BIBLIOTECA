from app.models import db
from app.models import Libro
from app.models import Ejemplar
from app.models import Prestamo
from datetime import datetime, timedelta


def agregar_libro(titulo, autor, isbn_base, cantidad, **otros_campos):
    nuevo_libro = Libro(
        titulo=titulo,
        autor=autor,
        isbn_base=isbn_base,
        cantidad_total=cantidad,
        cantidad_disponible=cantidad,
        **otros_campos
    )
    db.session.add(nuevo_libro)
    db.session.commit()  # Necesitamos el ID para crear los ejemplares

    for i in range(1, cantidad + 1):
        isbn = f"{isbn_base}{str(i).zfill(5)}"  # Ej: 987 + 00001
        ejemplar = Ejemplar(
            libro_id=nuevo_libro.id,
            isbn=isbn,
            estado='disponible'
        )
        db.session.add(ejemplar)

    db.session.commit()
    return nuevo_libro

def actualizar_disponibilidad_libro(libro):
    disponibles = Ejemplar.query.filter_by(libro_id=libro.id, estado='disponible').count()
    libro.cantidad_disponible = disponibles
    libro.disponible = disponibles > 0
    db.session.commit()


def prestar_por_isbn(isbn, usuario_id):
    ejemplar = Ejemplar.query.filter_by(isbn=isbn).first()

    if not ejemplar or ejemplar.estado != 'disponible':
        return "Ejemplar no disponible o no existe"

    prestamo = Prestamo(
        libro_id=ejemplar.libro_id,
        usuario_id=usuario_id,
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_esperada=datetime.utcnow().date() + timedelta(days=7),
        estado='prestado'
    )

    ejemplar.estado = 'prestado'
    db.session.add(prestamo)
    db.session.commit()

    actualizar_disponibilidad_libro(ejemplar.libro)
    return "Préstamo realizado correctamente"
