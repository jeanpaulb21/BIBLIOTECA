from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from time import time
import os
import requests
# Importa las extensiones correctamente
from app.extensions import db, login_manager, mail
from app.models import Usuario, Libro, Prestamo, Reserva, Favorito
from app.forms import RegistroForm, LibroForm, EditarLibroForm
from app.utils import verificar_token, generar_token
from app.libro import prestar_libro, devolver_libro



main = Blueprint('main', __name__)
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def roles_requeridos(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main.route('/')
def index():
    return render_template('login.html')

@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        username = form.username.data
        correo = form.correo.data  # NUEVO
        password = form.password.data

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('main.registro'))

        if Usuario.query.filter_by(correo=correo).first():  # NUEVO
            flash('Correo no disponible', 'error')
            return redirect(url_for('main.registro'))

        nuevo_usuario = Usuario(
            username=username,
            correo=correo,       # NUEVO
            rol='lector',
            activo=True
        )
        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso, ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('registro.html', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(correo=correo, activo=True).first()
        if usuario and usuario.check_password(password):
            login_user(usuario)
            flash('Has iniciado sesión.', 'success')

            if usuario.rol == 'administrador':
                    return redirect(url_for('main.inicio'))
            elif usuario.rol == 'bibliotecario':
                    return redirect(url_for('main.gestion'))
            elif usuario.rol == 'lector':
                    return redirect(url_for('main.catalogo'))
            else:
                    return redirect(url_for('main.index'))

    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('main.index'))

@main.route('/usuarios')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@main.route('/usuarios/<int:usuario_id>/toggle', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def toggle_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.username == 'admin':
        flash('No se puede desactivar al administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    if current_user.rol == 'bibliotecario' and usuario.rol == 'administrador':
        flash('No tienes permiso para modificar a un administrador.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f"El usuario '{usuario.username}' ha sido {estado}.", 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/usuarios/<int:usuario_id>/cambiar_rol', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def cambiar_rol(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.username == 'admin':
        flash('No se puede cambiar el rol del administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    nuevo_rol = request.form.get('rol')
    roles_permitidos = ['lector', 'bibliotecario']

    if nuevo_rol not in roles_permitidos:
        flash('Solo puedes cambiar roles entre lector y bibliotecario.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash(f"El rol del usuario '{usuario.username}' ha sido cambiado a {nuevo_rol}.", 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/admin/inicio', endpoint='inicio')
@login_required
@roles_requeridos('administrador')
def admin_inicio():
    return render_template('admin.html', version=time())

@main.route('/admin/inicio-contenido')
@login_required
@roles_requeridos('administrador')
def inicio_contenido():
    total_administradores = Usuario.query.filter_by(rol='administrador').count()
    total_lectores = Usuario.query.filter_by(rol='lector').count()
    total_libros = Libro.query.count()
    total_prestamos = Prestamo.query.count() if 'Prestamo' in globals() else 0
    total_reservas = Reserva.query.count() if 'Reserva' in globals() else 0


    return render_template('inicio.html',
        total_administradores=total_administradores,
        total_lectores=total_lectores,
        total_libros=total_libros,
        total_prestamos=total_prestamos,
        total_reservas=total_reservas,

    )


@main.route('/api/datos_libro/<isbn>')
def api_datos_libro(isbn):
    # Busca en OpenLibrary
    ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    response = requests.get(ol_url)
    data = response.json()

    portada_url = None # Inicializa la URL de la portada

    if f"ISBN:{isbn}" in data:
        libro = data[f"ISBN:{isbn}"]
        titulo = libro.get('title', '')
        autores = ', '.join(a['name'] for a in libro.get('authors', []))
        editorial = ', '.join(p['name'] for p in libro.get('publishers', [])) if 'publishers' in libro else ''
        fecha = libro.get('publish_date', None)

        # 🖼️ Obtener la URL de la portada
        if 'cover' in libro and 'large' in libro['cover']:
            portada_url = libro['cover']['large']
        elif 'cover' in libro and 'medium' in libro['cover']:
            portada_url = libro['cover']['medium']
        elif 'cover' in libro and 'small' in libro['cover']:
            portada_url = libro['cover']['small']
        # Si no hay cover en la data, se puede intentar con el API de Covers
        elif isbn:
            portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
            # Puedes incluso verificar si la imagen existe antes de enviarla
            # response_cover = requests.head(portada_url)
            # if not response_cover.ok:
            #     portada_url = None # O una URL de imagen por defecto

        return jsonify({
            "success": True,
            "titulo": titulo,
            "autor": autores,
            "editorial": editorial,
            "fecha_publicacion": fecha,
            "isbn": isbn,
            "portada_url": portada_url # Devolver la URL de la portada
        })

    return jsonify({"success": False})



@main.route('/api/dashboard_data')
@login_required
@roles_requeridos('administrador')
def dashboard_data():
    data = {
        'total_administradores': Usuario.query.filter_by(rol='administrador').count(),
        'total_lectores': Usuario.query.filter_by(rol='lector').count(),
        'total_libros': Libro.query.count(),
        'total_prestamos': Prestamo.query.count() if 'Prestamo' in globals() else 0,
        'total_reservas': Reserva.query.count() if 'Reserva' in globals() else 0,

    }
    return jsonify(data)

@main.route('/admin/usuarios')
@login_required
@roles_requeridos('administrador')
def admin_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@main.route('/admin/libros')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def admin_libros():
    # solo los que NO esten eliminados
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    return render_template('libros.html', libros=libros)

@main.route('/admin/prestamos')
@login_required
@roles_requeridos('administrador')
def admin_prestamos():
    return render_template('prestamos.html')

@main.route('/admin/prestamos/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_prestamos():
    prestamos = Prestamo.query.all()
    return render_template('prestamos_tabla.html', prestamos=prestamos)


@main.route('/admin/prestamos/nuevo')
@login_required
@roles_requeridos('administrador')
def nuevo_prestamo():
    usuarios = Usuario.query.all()
    libros = Libro.query.filter(Libro.estado != 'eliminado', Libro.cantidad_disponible > 0).all()
    return render_template('prestamos_agregar.html', usuarios=usuarios, libros=libros)


@main.route('/admin/reservas')
@login_required
@roles_requeridos('administrador')
def admin_reservas():
    return render_template('reservas.html')

@main.route('/admin/reportes')
@login_required
@roles_requeridos('administrador')
def admin_reportes():
    return render_template('reportes.html')


@main.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    usuario = Usuario.query.get(current_user.id)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        archivo = request.files.get('foto_perfil')

        if nombre:
            usuario.username = nombre  # Cambia esto si usas otro campo para el nombre
        if correo:
            usuario.correo = correo

        if archivo and archivo.filename != '':
            # Guardar la nueva imagen
            filename = secure_filename(archivo.filename)
            extension = os.path.splitext(filename)[1]
            nuevo_nombre = f"user_{usuario.id}{extension}"
            ruta_guardado = os.path.join(current_app.root_path, 'static', 'fotos_perfil', nuevo_nombre)
            archivo.save(ruta_guardado)

            usuario.foto = nuevo_nombre

        db.session.commit()
        flash("Perfil actualizado correctamente", "success")
        return redirect(url_for('main.configuracion'))

    return render_template('configuracion.html', usuario=usuario)


@main.route('/catalogo')
@login_required
def catalogo():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    # Para los lectores, podríamos querer información adicional como si el libro está en sus favoritos
    favoritos_ids = []
    if current_user.is_authenticated:
        if current_user.rol == 'lector':
            favoritos_ids = [f.libro_id for f in current_user.favoritos]

    return render_template('catalogo.html', libros=libros, favoritos_ids=favoritos_ids)

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)

# En routes.py
@main.route('/admin/usuarios/agregar')
@login_required
@roles_requeridos('administrador')
def agregar_usuario():
    form = RegistroForm()
    return render_template('registro_fragmento.html', form=form)

@main.route('/admin/usuarios/editar_formulario/<int:id>')
@login_required
@roles_requeridos('administrador')
def editar_formulario_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    return render_template('partials/usuarios_editar.html', usuario=usuario)


@main.route("/admin/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario eliminado"})


@main.route('/admin/libros/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def nuevo_libro():
    form = LibroForm()
    isbn_param = request.args.get('isbn')
    if isbn_param and request.method == 'GET':
        # Rellenar automáticamente desde OpenLibrary
        resp = requests.get(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_param}&format=json&jscmd=data")
        data = resp.json().get(f"ISBN:{isbn_param}", {})
        form.isbn.data = isbn_param
        form.titulo.data = data.get('title', '')
        form.autor.data = ', '.join([a['name'] for a in data.get('authors', [])]) if data.get('authors') else ''
        form.editorial.data = ', '.join([p['name'] for p in data.get('publishers', [])]) if data.get('publishers') else ''

        # 📖 Añadir la descripción si existe
        description = data.get('description')
        if isinstance(description, dict):
            form.descripcion.data = description.get('value', '')
        elif isinstance(description, str):
            form.descripcion.data = description
        else:
            form.descripcion.data = ''

        raw_date = data.get('publish_date', '')
        if raw_date:
            try:
                if len(raw_date) == 4 and raw_date.isdigit():
                    raw_date = f"{raw_date}-01-01"
                form.fecha_publicacion.data = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                form.fecha_publicacion.data = None

        # 🖼️ Obtener la URL de la portada y rellenar el formulario
        portada_url = None
        if 'cover' in data and 'large' in data['cover']:
            portada_url = data['cover']['large']
        elif 'cover' in data and 'medium' in data['cover']:
            portada_url = data['cover']['medium']
        elif 'cover' in data and 'small' in data['cover']:
            portada_url = data['cover']['small']
        elif isbn_param:
            portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn_param}-L.jpg?default=false"
            try:
                check_resp = requests.head(portada_url)
                if not check_resp.ok:
                    portada_url = None
            except requests.exceptions.RequestException:
                portada_url = None

        form.portada_url.data = portada_url # Asignar la URL al campo del formulario

    if form.validate_on_submit():
        isbn = form.isbn.data
        libro_existente = Libro.query.filter_by(isbn=isbn).first()
        if libro_existente:
            flash('Ya existe un libro con ese ISBN.', 'danger')
        else:
            cantidad_total = form.cantidad_total.data or 0
            nuevo_libro = Libro(
                isbn=isbn,
                titulo=form.titulo.data,
                autor=form.autor.data,
                descripcion=form.descripcion.data,
                categoria=form.categoria.data,
                editorial=form.editorial.data,
                fecha_publicacion=form.fecha_publicacion.data,
                cantidad_total=cantidad_total,
                cantidad_disponible=cantidad_total,
                portada_url=form.portada_url.data # Guardar la URL de la portada
            )
            nuevo_libro.actualizar_estado()

            db.session.add(nuevo_libro)
            db.session.commit()

            flash('Libro creado exitosamente.', 'success')
            return redirect(url_for('main.admin_libros'))

    return render_template('nuevo_libro.html', form=form)


@main.route('/admin/libros/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_libros():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    return render_template('libros_tabla.html', libros=libros)


@main.route('/admin/libros/eliminar/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def eliminar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    # Solo eliminamos si no hay préstamos activos
    if libro.cantidad_disponible < libro.cantidad_total:
        flash('No se puede eliminar: hay ejemplares prestados.', 'danger')
        return redirect(url_for('main.admin_libros'))

    libro.marcar_como_eliminado()
    db.session.commit()
    flash('Libro marcado como eliminado.', 'success')
    return redirect(url_for('main.admin_libros'))



@main.route('/admin/libros/editar/<int:libro_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def editar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    form = EditarLibroForm(obj=libro)

    if form.validate_on_submit():
        # Nueva cantidad total y cantidad disponible del formulario
        nueva_cantidad_total = form.cantidad_total.data
        nueva_cantidad_disponible = form.cantidad_disponible.data

        # Validar que la cantidad disponible nunca sea mayor que la cantidad total
        if nueva_cantidad_disponible > nueva_cantidad_total:
            flash("La cantidad disponible no puede ser mayor que la cantidad total.", "danger")
            return redirect(url_for('main.editar_libro', libro_id=libro_id))

        # Actualizar campos del libro
        libro.titulo = form.titulo.data
        libro.autor = form.autor.data
        libro.categoria = form.categoria.data
        libro.descripcion = form.descripcion.data
        libro.editorial = form.editorial.data
        libro.fecha_publicacion = form.fecha_publicacion.data
        libro.cantidad_total = nueva_cantidad_total
        libro.cantidad_disponible = nueva_cantidad_disponible
        libro.disponible = nueva_cantidad_total > 0  # Disponible solo si hay al menos un ejemplar

        # Guardar cambios
        db.session.commit()
        flash('Libro editado exitosamente.', 'success')
        return redirect(url_for('main.admin_libros'))

    return render_template('editar_libro.html', form=form, libro=libro)


import requests

@main.route('/admin/libros/scan', methods=['GET'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def escanear_libro():
    return render_template('escanear_libro.html')


@main.route('/admin/reservas/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_reserva():
    datos = request.get_json()
    libro_id = datos.get('libro_id')
    usuario_id = datos.get('usuario_id') # Asume que el ID de usuario viene en los datos si es diferente al current_user
    fecha_expiracion_str = datos.get('fecha_expiracion')

    if not libro_id or not usuario_id or not fecha_expiracion_str:
        return jsonify({'mensaje': 'Datos incompletos para la reserva.'}), 400

    try:
        fecha_expiracion = datetime.strptime(fecha_expiracion_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'mensaje': 'Formato de fecha inválido.'}), 400

    # Verificar disponibilidad del libro para reservar
    libro = Libro.query.get(libro_id)
    if not libro or libro.estado == 'eliminado' or libro.cantidad_disponible == 0:
        return jsonify({'mensaje': 'Libro no disponible para reserva.'}), 400

    # Crear la reserva
    nueva_reserva = Reserva(
        libro_id=libro_id,
        usuario_id=usuario_id,
        fecha_expiracion=fecha_expiracion,
        estado='activa'
    )
    db.session.add(nueva_reserva)
    db.session.commit()
    return jsonify({'mensaje': 'Reserva realizada correctamente'})

@main.route('/admin/prestamos/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_prestamo():
    datos = request.get_json()
    libro_id = datos.get('libro_id')
    usuario_id = datos.get('usuario_id')
    fecha_devolucion_esperada_str = datos.get('fecha_devolucion_esperada')

    if not libro_id or not usuario_id or not fecha_devolucion_esperada_str:
        return jsonify({'mensaje': 'Datos incompletos para el préstamo.'}), 400

    try:
        fecha_devolucion_esperada = datetime.strptime(fecha_devolucion_esperada_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'mensaje': 'Formato de fecha inválido.'}), 400

    # Verificar disponibilidad del libro para préstamo
    libro = Libro.query.get(libro_id)
    if not libro or libro.estado == 'eliminado' or libro.cantidad_disponible <= 0:
        return jsonify({'mensaje': 'Libro no disponible para préstamo.'}), 400

    # Crear el préstamo
    nuevo_prestamo = Prestamo(
        libro_id=libro_id,
        usuario_id=usuario_id,
        fecha_devolucion_esperada=fecha_devolucion_esperada,
        estado='prestado'
    )
    db.session.add(nuevo_prestamo)

    # Actualizar la cantidad disponible del libro
    libro.cantidad_disponible -= 1
    libro.actualizar_estado() # Actualizar el estado del libro (ej. a "prestados" si se agotan)

    db.session.commit()
    return jsonify({'mensaje': 'Préstamo registrado correctamente'})


# en routes.py
@main.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        usuario = Usuario.query.get(current_user.id)
        usuario.nombre = request.form['nombre']
        usuario.correo = request.form['correo']

        # Si hay una nueva foto de perfil
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file.filename != '':
                filename = secure_filename(file.filename)
                ruta_carpeta = os.path.join('static', 'imagenes', 'perfil')
                os.makedirs(ruta_carpeta, exist_ok=True)  # Crea carpeta si no existe
                filepath = os.path.join(ruta_carpeta, filename)
                file.save(filepath)
                usuario.foto = f'imagenes/perfil/{filename}'

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('main.perfil'))

    return render_template('perfil.html', usuario=current_user)

@main.route('/foto_perfil')
@login_required
def foto_perfil():
    if current_user.foto:
        ruta = os.path.join('static', current_user.foto.replace('/', os.sep))
        if os.path.exists(ruta):
            return send_file(ruta, mimetype='image/jpeg')
    
    # Si no tiene foto, o no existe el archivo
    return redirect(url_for('static', filename='imagenes/perfil/default.png'))

@main.route('/libro/<int:libro_id>')
@login_required
def detalle_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    es_favorito = False
    if current_user.is_authenticated and current_user.rol == 'lector':
        es_favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first() is not None
    return render_template('detalle_libro.html', libro=libro, es_favorito=es_favorito)

@main.route('/favoritos/toggle/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('lector')
def toggle_favorito(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first()

    if favorito:
        db.session.delete(favorito)
        flash('Libro eliminado de tus favoritos.', 'info')
    else:
        nuevo_favorito = Favorito(usuario_id=current_user.id, libro_id=libro.id)
        db.session.add(nuevo_favorito)
        flash('Libro añadido a tus favoritos.', 'success')

    db.session.commit()
    return redirect(url_for('main.detalle_libro', libro_id=libro.id))

@main.route('/mis_libros')
@login_required
@roles_requeridos('lector')
def mis_libros():
    # Obtener préstamos activos del usuario
    mis_prestamos = Prestamo.query.filter_by(usuario_id=current_user.id, estado='prestado').all()
    # Obtener reservas activas del usuario
    mis_reservas = Reserva.query.filter_by(usuario_id=current_user.id, estado='activa').all()
    # Obtener favoritos del usuario
    mis_favoritos = Favorito.query.filter_by(usuario_id=current_user.id).all()

    return render_template('mis_libros.html',
                           prestamos=mis_prestamos,
                           reservas=mis_reservas,
                           favoritos=mis_favoritos)

@main.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            token = generar_token(usuario.correo)
            link = url_for('main.restablecer', token=token, _external=True)

            msg = Message('Recuperar contraseña', sender='noreply@biblioteca.com', recipients=[usuario.correo])
            msg.body = (
                        f'Estimado usuario,\n\n'
                        f'Hemos recibido una solicitud para restablecer la contraseña de su cuenta de biblioteca avocado.\n'
                        f'Para continuar con el proceso, por favor haga clic en el siguiente enlace:\n\n'
                        f'{link}\n\n'
                        f'Si usted no solicitó este cambio, puede ignorar este mensaje.\n\n'
                        f'Atentamente,\n'
                        f'El equipo de la Biblioteca'
                    )

            mail.send(msg)

            flash('Te enviamos un correo para recuperar tu contraseña.', 'info')
        else:
            flash('Correo no encontrado.', 'danger')
    return render_template('recuperar.html')

@main.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    email = verificar_token(token)
    if not email:
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        nueva_pass = request.form['password']
        usuario = Usuario.query.filter_by(correo=email).first()
        if usuario:
            usuario.set_password(nueva_pass)
            db.session.commit()
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('main.login'))
    return render_template('restablecer.html')

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')
def usuarios_modal():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)

