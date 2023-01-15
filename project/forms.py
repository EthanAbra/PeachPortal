from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SubmitField, StringField, RadioField, IntegerField
from wtforms import SelectMultipleField, FieldList, FormField, SelectField, HiddenField 
from flask_bootstrap import SwitchField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask import Markup

def analysis_toggle():
    toggle_value = Markup('<span class="slider round"></span>')
    toggle_button = BooleanField(toggle_value)
    return toggle_button

class LoginForm(FlaskForm):
    email = StringField('Email',
            validators=[DataRequired(), Length(1, 120), Email()])
    password = PasswordField('Password', validators=[DataRequired(),  
                                                    Length(min=2, message='Password should be at least %(min)d characters long')])
    submit = SubmitField('Log In')
    
    
class SignupForm(FlaskForm):
    first = StringField('First Name',
            validators=[DataRequired()])
    last = StringField('Last Name',
        validators=[DataRequired()])
    classId = IntegerField('Class',
        validators=[DataRequired()])
    email = StringField('Email',
            validators=[DataRequired(), Length(1, 120), Email()])
    side = RadioField('Side', choices=[('port', 'Port'), ('starboard', 'Starboard'), ('cox', 'Coxswain')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),  
                                                    Length(min=8, message='Password should be at least %(min)d characters long')])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    teamId = IntegerField('Team',
        validators=[DataRequired()])
    submit = SubmitField('Sign Up')


    
class AthleteForm(FlaskForm):
    athleteId = HiddenField('AthleteId')
    namestring = StringField('Name',
            validators=[DataRequired()])
    side = SelectField('Side', choices=[('port', 'Port'), ('starboard', 'Starboard'), ('cox', 'Coxswain')], validators=[DataRequired()])
    classId = IntegerField('ClassId')  
    permissions = SelectMultipleField('Permissions', choices=[('admin', 'View/Edit Team'), ('cox', 'View/Edit all Workouts')])
    renders = SelectMultipleField('Renders', choices=[('slip', 'Slip'), ('wash', 'Wash'), ('power', 'Power'), ('percentage', 'Max Force %')])
    active = BooleanField('Active')
    

class TeamForm(FlaskForm):
    submit = SubmitField('Save Changes')
    athletes = FieldList(FormField(AthleteForm))
    analysis = analysis_toggle()
    
    
class RegisterForm(FlaskForm):
    submit = SubmitField('Register Team')
    teamName = StringField('Team Name',
            validators=[DataRequired()])
    