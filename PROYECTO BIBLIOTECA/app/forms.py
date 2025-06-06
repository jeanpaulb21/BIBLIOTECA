from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError, Optional, NumberRange
from app.models import Usuario

class RegistroForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$', message='La contraseña debe ser alfanumérica (letras y números).')
    ])
    confirmar_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    submit = SubmitField('Registrarse')

    def validate_username(self, username):
        usuario = Usuario.query.filter_by(username=username.data).first()
        if usuario:
            raise ValidationError('El nombre de usuario ya está en uso. Por favor elige otro.')

class LibroForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=150)])
    autor = StringField('Autor', validators=[DataRequired(), Length(max=100)])
    isbn_base = StringField('ISBN', validators=[Optional(), Length(max=20)])
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=500)])
    # Si tienes campos extras, por ejemplo:
    # editorial = StringField('Editorial', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Guardar')
