from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app.models import db, Usuario, Libro, Prestamo, Reserva
from app.forms import RegistroForm, LibroForm
from functools import wraps
import random

main = Blueprint('main', __name__)

login_manager = LoginManager()
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
    return render_template('index.html')

@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('main.registro'))

        nuevo_usuario = Usuario(
            username=username,
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
        username = request.form['username']
        password = request.form['password']

        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        if usuario and usuario.check_password(password):
            login_user(usuario)
            flash('Has iniciado sesión.', 'success')

            if usuario.rol == 'administrador':
                    return redirect(url_for('main.inicio'))
            elif usuario.rol == 'bibliotecario':
                    return redirect(url_for('main.gestion'))
            elif usuario.rol == 'lector':
                    return redirect(url_for('main.lectores'))
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
    return render_template('admin.html')

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
@roles_requeridos('administrador')
def admin_libros():
    libros = Libro.query.all()
    return render_template('libros.html', libros=libros)

@main.route('/admin/prestamos')
@login_required
@roles_requeridos('administrador')
def admin_prestamos():
    return render_template('prestamos.html')

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

@main.route('/admin/configuracion')
@login_required
@roles_requeridos('administrador')
def admin_configuracion():
    return render_template('configuracion.html')

@main.route('/lectores')
@login_required
@roles_requeridos('lector')
def lectores():
    return render_template('lectores.html')  

@main.route('/catalogo')
@login_required
def catalogo():
    libros = Libro.query.all()
    return render_template('catalogo.html', libros=libros)

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')  # Si usas roles
def mostrar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)



@main.route("/admin/usuarios/editar", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def editar_usuario():
    datos = request.get_json()
    usuario = Usuario.query.get(datos["id"])
    usuario.nombre = datos["nombre"]
    usuario.email = datos["email"]
    usuario.rol = datos["rol"]
    db.session.commit()
    return jsonify({"mensaje": "Usuario actualizado"})

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

    if form.validate_on_submit():
        nuevo_libro = Libro(
            titulo=form.titulo.data,
            autor=form.autor.data,
            descripcion=form.descripcion.data,
            isbn_base=form.isbn_base.data if form.isbn_base.data else f"987{random.randint(1000000, 9999999)}"
        )

        # Validar ISBN duplicado
        if Libro.query.filter_by(isbn_base=nuevo_libro.isbn_base).first():
            flash("Ya existe un libro con este ISBN.", "danger")
            return redirect(url_for('main.nuevo_libro'))

        try:
            db.session.add(nuevo_libro)
            db.session.commit()
            flash("Libro agregado exitosamente.", "success")
            return redirect(url_for('main.admin_libros'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al agregar libro: {e}", "danger")

    return render_template('nuevo_libro.html', form=form)

@main.route('/admin/libros/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_libros():
    libros = Libro.query.all()
    return render_template('libros_tabla.html', libros=libros)

@main.route('/admin/reservas/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_reserva():
    datos = request.get_json()
    print('Reserva recibida:', datos)
    # Guardar en tabla si tienes el modelo Reserva
    return jsonify({'mensaje': 'Reserva realizada correctamente'})

@main.route('/admin/prestamos/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_prestamo():
    datos = request.get_json()
    print('Préstamo recibido:', datos)
    # Guardar en tabla si tienes el modelo Prestamo
    return jsonify({'mensaje': 'Préstamo registrado correctamente'})
